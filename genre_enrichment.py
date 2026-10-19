import logging
from types import MappingProxyType
from typing import NamedTuple

import pandas as pd
import requests

from etl import GENRE_TABLE, TRACK_GENRE_TABLE, TRACK_TABLE
from transformers import GenreTransformer, TrackGenreTransformer, TrackMerger

logger = logging.getLogger(__name__)


class GenreSearchResult(NamedTuple):
    source_track_df: pd.DataFrame
    # Tracks iTunes answered for, whether or not a song matched; failed searches
    # are left out so they're retried on the next run
    searched_track_df: pd.DataFrame


class GenreEnricher:
    TRACK_ID_COLUMN = "track_id"
    GENRE_SEARCHED_AT_COLUMN = "genre_searched_at"
    GENRE_NAME_COLUMN = "name"
    GENRE_COLUMN = "genre"
    IS_EXPLICIT_COLUMN = "is_explicit"
    TITLE_COLUMN = "title"
    ARTIST_NAME_COLUMN = "artist_name"

    def __init__(self):
        self._genre_transformer = GenreTransformer()

    def select_missing(self, track_df, track_genre_df):
        has_genre = track_df[self.TRACK_ID_COLUMN].isin(
            track_genre_df[self.TRACK_ID_COLUMN]
        )
        was_searched = track_df[self.GENRE_SEARCHED_AT_COLUMN].notna()
        return track_df[~has_genre & ~was_searched]

    def select_new_genres(self, source_track_df, genre_df):
        found_genre_df = self._genre_transformer.transform(source_track_df)
        is_loaded = found_genre_df[self.GENRE_NAME_COLUMN].isin(
            genre_df[self.GENRE_NAME_COLUMN]
        )
        return found_genre_df[~is_loaded]

    def select_explicit(self, source_track_df):
        return source_track_df[[self.TRACK_ID_COLUMN, self.IS_EXPLICIT_COLUMN]].dropna(
            subset=[self.IS_EXPLICIT_COLUMN]
        )


class TrackGenreEnricher(GenreEnricher):
    SEARCH_TIME_ZONE = "UTC"
    SEARCH_POSITION_COLUMN = "search_position"
    ITUNES_TRACK_NAME_FIELD = "trackName"
    ITUNES_ARTIST_NAME_FIELD = "artistName"
    ITUNES_GENRE_FIELD = "primaryGenreName"
    ITUNES_RELEASE_DATE_FIELD = "releaseDate"
    ITUNES_EXPLICITNESS_FIELD = "trackExplicitness"
    # A "cleaned" track is the edited version of an explicit song
    ITUNES_EXPLICITNESS_VALUES = MappingProxyType(
        {
            "explicit": True,
            "cleaned": True,
            "notExplicit": False,
        }
    )
    ITUNES_FIELD_RENAMES = MappingProxyType(
        {
            ITUNES_TRACK_NAME_FIELD: TrackMerger.TRACK_NAME_COLUMN,
            ITUNES_ARTIST_NAME_FIELD: TrackMerger.ARTIST_NAME_COLUMN,
            ITUNES_GENRE_FIELD: GenreEnricher.GENRE_COLUMN,
        }
    )
    ITUNES_RESULT_COLUMNS = (
        *ITUNES_FIELD_RENAMES,
        ITUNES_RELEASE_DATE_FIELD,
        ITUNES_EXPLICITNESS_FIELD,
        SEARCH_POSITION_COLUMN,
    )

    def __init__(self, create_client):
        super().__init__()
        self._create_client = create_client
        self._merger = TrackMerger()

    def enrich(self, track_df):
        logger.info("Searching iTunes for genres of %d tracks", len(track_df))
        searched_at = pd.Timestamp.now(tz=self.SEARCH_TIME_ZONE)
        with self._create_client() as client:
            results_by_track_id = {
                track.track_id: self._search_track(client, track)
                for track in track_df.itertuples(index=False)
            }
        searched_results_by_track_id = {
            track_id: results
            for track_id, results in results_by_track_id.items()
            if results is not None
        }
        itunes_df = self._build_itunes_df(
            [
                result
                for results in searched_results_by_track_id.values()
                for result in results
            ]
        )
        source_track_df = self._merger.transform(
            self._build_billboard_df(track_df), itunes_df
        ).dropna(subset=[self.GENRE_COLUMN])
        searched_track_df = pd.DataFrame(
            {
                self.TRACK_ID_COLUMN: list(searched_results_by_track_id),
                self.GENRE_SEARCHED_AT_COLUMN: searched_at,
            }
        )
        logger.info(
            "Found iTunes genres for %d of %d tracks (%d searches failed)",
            len(source_track_df),
            len(track_df),
            len(track_df) - len(searched_track_df),
        )
        return GenreSearchResult(source_track_df, searched_track_df)

    def _search_track(self, client, track):
        try:
            results = client.search_songs(
                track.title, self._merger.get_primary_artist(track.artist_name)
            )
        except requests.RequestException as error:
            logger.warning(
                "iTunes search failed for %s - %s (%s: %s)",
                track.title,
                track.artist_name,
                type(error).__name__,
                error,
            )
            return None
        return [
            {**result, self.SEARCH_POSITION_COLUMN: search_position}
            for search_position, result in enumerate(results)
        ]

    def _build_itunes_df(self, results):
        result_df = pd.DataFrame(results, columns=list(self.ITUNES_RESULT_COLUMNS))
        release_dates = pd.to_datetime(
            result_df[self.ITUNES_RELEASE_DATE_FIELD], errors="coerce", utc=True
        )
        return result_df.rename(columns=self.ITUNES_FIELD_RENAMES).assign(
            **{
                TrackMerger.CANDIDATE_YEAR_COLUMN: release_dates.dt.year,
                self.IS_EXPLICIT_COLUMN: result_df[self.ITUNES_EXPLICITNESS_FIELD].map(
                    self.ITUNES_EXPLICITNESS_VALUES
                ),
                # Earlier search results rank higher, like Spotify popularity
                TrackMerger.CANDIDATE_POPULARITY_COLUMN: -result_df[
                    self.SEARCH_POSITION_COLUMN
                ],
            }
        )[
            [
                TrackMerger.TRACK_NAME_COLUMN,
                TrackMerger.ARTIST_NAME_COLUMN,
                self.GENRE_COLUMN,
                self.IS_EXPLICIT_COLUMN,
                TrackMerger.CANDIDATE_YEAR_COLUMN,
                TrackMerger.CANDIDATE_POPULARITY_COLUMN,
            ]
        ]

    def _build_billboard_df(self, track_df):
        return (
            track_df[[self.TRACK_ID_COLUMN, self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN]]
            .rename(columns={self.TITLE_COLUMN: TrackMerger.TRACK_NAME_COLUMN})
            .reset_index(drop=True)
        )


# Replays genres saved from earlier iTunes searches instead of searching again
class SnapshotGenreEnricher(GenreEnricher):
    def __init__(self, snapshot_df):
        super().__init__()
        self._snapshot_df = snapshot_df

    def enrich(self, track_df):
        snapshot_track_df = track_df[
            [self.TRACK_ID_COLUMN, self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN]
        ].merge(self._snapshot_df, on=[self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN])
        source_track_df = (
            snapshot_track_df.dropna(subset=[self.GENRE_COLUMN])
            .rename(columns={self.TITLE_COLUMN: TrackMerger.TRACK_NAME_COLUMN})
            .drop(columns=[self.GENRE_SEARCHED_AT_COLUMN])
        )
        searched_track_df = snapshot_track_df.dropna(
            subset=[self.GENRE_SEARCHED_AT_COLUMN]
        )[[self.TRACK_ID_COLUMN, self.GENRE_SEARCHED_AT_COLUMN]]
        logger.info(
            "Restored genres for %d of %d tracks from the snapshot",
            len(source_track_df),
            len(track_df),
        )
        return GenreSearchResult(source_track_df, searched_track_df)


class GenreEnrichmentProcessor:
    def __init__(self, extractor, loader, enricher):
        self._extractor = extractor
        self._loader = loader
        self._enricher = enricher

    def select_pending(self):
        track_df = self._extractor.extract_from_db(TRACK_TABLE)
        missing_track_df = self._enricher.select_missing(
            track_df, self._extractor.extract_from_db(TRACK_GENRE_TABLE)
        )
        logger.info(
            "%d of %d tracks are missing a genre", len(missing_track_df), len(track_df)
        )
        return missing_track_df

    def compute_batch(self, track_batch_df):
        return track_batch_df, self._enricher.enrich(track_batch_df)

    def load_batch(self, batch_result):
        track_batch_df, (source_track_df, searched_track_df) = batch_result
        new_genre_df = self._enricher.select_new_genres(
            source_track_df, self._extractor.extract_from_db(GENRE_TABLE)
        )
        self._loader.load_to_db(new_genre_df, GENRE_TABLE)
        track_genre_df = TrackGenreTransformer().transform(
            track_batch_df,
            self._extractor.extract_from_db(GENRE_TABLE),
            source_track_df,
        )
        self._loader.load_to_db(track_genre_df, TRACK_GENRE_TABLE)
        self._loader.update_db(
            self._enricher.select_explicit(source_track_df),
            TRACK_TABLE,
            GenreEnricher.TRACK_ID_COLUMN,
        )
        self._loader.update_db(
            searched_track_df, TRACK_TABLE, GenreEnricher.TRACK_ID_COLUMN
        )
