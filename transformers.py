import logging
import re
import unicodedata

import pandas as pd

logger = logging.getLogger(__name__)


class TrackMerger:
    WORD_SEPARATOR = " "
    UNICODE_DECOMPOSITION_FORM = "NFKD"
    PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
    WHITESPACE_PATTERN = re.compile(r"\s+")
    FEATURED_ARTIST_SEPARATOR = re.compile(r"\s+feat\.\s+", re.IGNORECASE)
    FEATURED_CREDIT_PATTERN = re.compile(
        r"\s*[(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+(?P<artists>[^)\]]+)[)\]]",
        re.IGNORECASE,
    )
    VERSION_SUFFIX_PATTERN = re.compile(
        r"\s*[(\[]\s*(?:remaster(?:ed)?(?:\s+\d{4})?|remix)\s*[)\]]"
        r"|\s*-\s*remaster(?:ed)?(?:\s+\d{4})?$",
        re.IGNORECASE,
    )
    TITLE_SUFFIX_PATTERN = re.compile(r"\s*[(\[][^)\]]*[)\]]|\s+-\s+.*$")
    TRACK_SUFFIX_PATTERNS = (VERSION_SUFFIX_PATTERN, TITLE_SUFFIX_PATTERN)
    ALTERNATE_VERSION_PATTERN = re.compile(
        r"\b(?:remix|live|acoustic|unplugged|mix|instrumental|demo|sessions?|extended"
        r"|orchestral|synthesis|dub|broadway)\b"
        r"|12\""
        r"|\b(?:rock|pop|country|spanish) version\b",
        re.IGNORECASE,
    )
    BILLBOARD_TO_SPOTIFY_ARTIST_NAMES = {"Pink": "P!nk"}
    BILLBOARD_ROW_COLUMN = "billboard_row"
    TRACK_NAME_COLUMN = "track_name"
    ARTIST_NAME_COLUMN = "artist_name"
    TRACK_MATCH_NAME_COLUMN = "track_match_name"
    ARTIST_MATCH_NAME_COLUMN = "artist_match_name"
    MATCH_NAME_COLUMNS = (TRACK_MATCH_NAME_COLUMN, ARTIST_MATCH_NAME_COLUMN)
    SPOTIFY_INDEX_COLUMN = "Unnamed: 0"
    SPOTIFY_TRACK_ID_COLUMN = "track_id"
    SPOTIFY_EXCLUDED_COLUMNS = (
        SPOTIFY_INDEX_COLUMN,
        SPOTIFY_TRACK_ID_COLUMN,
        TRACK_NAME_COLUMN,
        ARTIST_NAME_COLUMN,
    )
    SPOTIFY_COLUMN_SUFFIX = "_spotify"
    SPOTIFY_COLUMN_SUFFIXES = ("", SPOTIFY_COLUMN_SUFFIX)
    SPOTIFY_TRACK_NAME_COLUMN = f"{TRACK_NAME_COLUMN}{SPOTIFY_COLUMN_SUFFIX}"
    SPOTIFY_ARTIST_MATCH_NAME_COLUMN = (
        f"{ARTIST_MATCH_NAME_COLUMN}{SPOTIFY_COLUMN_SUFFIX}"
    )
    SPOTIFY_YEAR_COLUMN = "year"
    SPOTIFY_POPULARITY_COLUMN = "popularity"
    EXACT_ARTIST_MATCH_COLUMN = "is_exact_artist_match"
    TITLE_SUFFIX_COLUMN = "has_title_suffix"

    def transform(self, billboard_df, spotify_df):
        logger.info(
            "Matching %d Billboard rows to %d Spotify tracks",
            len(billboard_df),
            len(spotify_df),
        )
        spotify_column_names = spotify_df.columns.drop(
            list(self.SPOTIFY_EXCLUDED_COLUMNS)
        )
        candidate_df = self._find_candidates(billboard_df, spotify_df)
        best_match_df = self._select_best_matches(candidate_df)[spotify_column_names]
        logger.info(
            "Matched %d of %d Billboard rows to Spotify tracks",
            len(best_match_df),
            len(billboard_df),
        )
        return billboard_df.join(best_match_df)

    def _normalize_name(self, name):
        decomposed = unicodedata.normalize(
            self.UNICODE_DECOMPOSITION_FORM, name.casefold()
        )
        unaccented = "".join(
            char for char in decomposed if not unicodedata.combining(char)
        )
        return self.WHITESPACE_PATTERN.sub(
            self.WORD_SEPARATOR, self.PUNCTUATION_PATTERN.sub("", unaccented)
        ).strip()

    def _compact_name(self, name):
        return self.WHITESPACE_PATTERN.sub("", name)

    def _get_primary_artist(self, artist_name):
        primary_artist, *_featured_artists = self.FEATURED_ARTIST_SEPARATOR.split(
            artist_name
        )
        return primary_artist

    def _get_track_match_names(self, track_name):
        uncredited_name = self.FEATURED_CREDIT_PATTERN.sub("", track_name)
        return sorted(
            {
                self._compact_name(
                    self._normalize_name(suffix_pattern.sub("", uncredited_name))
                )
                for suffix_pattern in self.TRACK_SUFFIX_PATTERNS
            }
        )

    def _is_exact_artist_match(self, artist_match_name, spotify_artist_match_name):
        return self._compact_name(artist_match_name) == self._compact_name(
            spotify_artist_match_name
        )

    def _is_featured_artist_match(self, artist_match_name, spotify_artist_match_name):
        return artist_match_name.startswith(
            f"{spotify_artist_match_name}{self.WORD_SEPARATOR}"
        )

    def _add_match_names(self, df):
        match_name_df = df.assign(
            **{
                self.TRACK_MATCH_NAME_COLUMN: df[self.TRACK_NAME_COLUMN]
                .fillna("")
                .map(self._get_track_match_names),
                self.ARTIST_MATCH_NAME_COLUMN: (
                    df[self.ARTIST_NAME_COLUMN]
                    .fillna("")
                    .map(self._get_primary_artist)
                    .replace(self.BILLBOARD_TO_SPOTIFY_ARTIST_NAMES)
                    .map(self._normalize_name)
                ),
            }
        ).explode(self.TRACK_MATCH_NAME_COLUMN)
        has_match_names = (
            match_name_df[list(self.MATCH_NAME_COLUMNS)].ne("").all(axis="columns")
        )
        return match_name_df[has_match_names]

    def _find_candidates(self, billboard_df, spotify_df):
        billboard_match_df = self._add_match_names(billboard_df)[
            [self.TRACK_NAME_COLUMN, *self.MATCH_NAME_COLUMNS]
        ].reset_index(names=self.BILLBOARD_ROW_COLUMN)
        return billboard_match_df.merge(
            self._add_match_names(spotify_df),
            on=self.TRACK_MATCH_NAME_COLUMN,
            suffixes=self.SPOTIFY_COLUMN_SUFFIXES,
        )

    def _match_artists(self, candidate_df, is_artist_match):
        artist_match_name_pairs = zip(
            candidate_df[self.ARTIST_MATCH_NAME_COLUMN],
            candidate_df[self.SPOTIFY_ARTIST_MATCH_NAME_COLUMN],
        )
        return pd.Series(
            [
                is_artist_match(*artist_match_name_pair)
                for artist_match_name_pair in artist_match_name_pairs
            ],
            index=candidate_df.index,
        )

    def _is_matching_version(self, candidate_df):
        spotify_version_suffixes = (
            candidate_df[self.SPOTIFY_TRACK_NAME_COLUMN]
            .fillna("")
            .str.findall(self.TITLE_SUFFIX_PATTERN)
            .str.join(self.WORD_SEPARATOR)
        )
        return ~spotify_version_suffixes.str.contains(
            self.ALTERNATE_VERSION_PATTERN
        ) | candidate_df[self.TRACK_NAME_COLUMN].str.contains(
            self.ALTERNATE_VERSION_PATTERN, na=False
        )

    def _has_title_suffix(self, candidate_df):
        uncredited_names = (
            candidate_df[self.SPOTIFY_TRACK_NAME_COLUMN]
            .fillna("")
            .str.replace(self.FEATURED_CREDIT_PATTERN, "", regex=True)
        )
        return uncredited_names.str.contains(self.TITLE_SUFFIX_PATTERN)

    def _select_best_matches(self, candidate_df):
        is_exact_artist_match = self._match_artists(
            candidate_df, self._is_exact_artist_match
        )
        is_artist_match = is_exact_artist_match | self._match_artists(
            candidate_df, self._is_featured_artist_match
        )
        return (
            candidate_df.assign(
                **{
                    self.EXACT_ARTIST_MATCH_COLUMN: is_exact_artist_match,
                    self.TITLE_SUFFIX_COLUMN: self._has_title_suffix(candidate_df),
                }
            )[is_artist_match & self._is_matching_version(candidate_df)]
            .sort_values(
                [
                    self.EXACT_ARTIST_MATCH_COLUMN,
                    self.SPOTIFY_YEAR_COLUMN,
                    self.TITLE_SUFFIX_COLUMN,
                    self.SPOTIFY_POPULARITY_COLUMN,
                ],
                ascending=[False, True, True, False],
                kind="stable",
            )
            .drop_duplicates(subset=self.BILLBOARD_ROW_COLUMN)
            .set_index(self.BILLBOARD_ROW_COLUMN)
        )


class GenreTransformer:
    def transform(self, track_df):
        genre_df = (
            track_df["genre"]
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .to_frame(name="name")
        )
        genre_df["name"] = genre_df["name"].str.strip()
        logger.info("Built %d genres", len(genre_df))
        return genre_df


class ChartTransformer:
    def transform(self, track_df):
        chart_df = (
            track_df["chart_year"]
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .to_frame(name="year")
        )
        chart_df["year"] = chart_df["year"].astype(int)
        logger.info("Built %d charts", len(chart_df))
        return chart_df


class TrackTransformer:
    SONG_KEY_COLUMNS = ("track_name", "artist_name")
    CHART_YEAR_COLUMN = "chart_year"
    COLUMN_RENAMES = {"track_name": "title"}
    TRACK_COLUMNS = (
        "title",
        "artist_name",
        "lyrics",
        "danceability",
        "energy",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "loudness",
        "tempo",
        "key",
        "mode",
        "time_signature",
        "duration_ms",
    )
    INTEGER_COLUMNS = ("key", "mode", "time_signature", "duration_ms")
    NULLABLE_INTEGER_DTYPE = "Int64"

    def transform(self, track_df):
        song_df = (
            track_df.sort_values(self.CHART_YEAR_COLUMN, kind="stable")
            .drop_duplicates(subset=list(self.SONG_KEY_COLUMNS))
            .rename(columns=self.COLUMN_RENAMES)[list(self.TRACK_COLUMNS)]
            .astype(dict.fromkeys(self.INTEGER_COLUMNS, self.NULLABLE_INTEGER_DTYPE))
            .reset_index(drop=True)
        )
        logger.info(
            "Built %d unique tracks from %d chart rows", len(song_df), len(track_df)
        )
        return song_df


class TrackGenreTransformer:
    def transform(self, db_track_df, db_genre_df, source_track_df):
        track_df = db_track_df.merge(
            source_track_df[["track_name", "artist_name", "genre"]],
            how="left",
            left_on=["title", "artist_name"],
            right_on=["track_name", "artist_name"],
        ).drop(columns=["track_name"])
        track_genre_df = track_df.merge(
            db_genre_df, how="inner", left_on="genre", right_on="name"
        ).drop(columns=["genre", "name"])
        track_genre_df = track_genre_df[["track_id", "genre_id"]].drop_duplicates()
        logger.info(
            "Linked %d of %d tracks to a genre",
            track_genre_df["track_id"].nunique(),
            len(db_track_df),
        )
        return track_genre_df


class ChartTrackTransformer:
    def transform(self, db_track_df, db_chart_df, source_track_df):
        track_df = db_track_df.merge(
            source_track_df[["track_name", "artist_name", "chart_year", "rank"]],
            how="left",
            left_on=["title", "artist_name"],
            right_on=["track_name", "artist_name"],
        ).drop(columns=["track_name"])
        chart_track_df = track_df.merge(
            db_chart_df, how="inner", left_on="chart_year", right_on="year"
        ).drop(columns=["chart_year", "year"])
        chart_track_df = chart_track_df[
            ["track_id", "chart_id", "rank"]
        ].drop_duplicates()
        logger.info(
            "Linked %d of %d tracks to %d chart entries",
            chart_track_df["track_id"].nunique(),
            len(db_track_df),
            len(chart_track_df),
        )
        return chart_track_df


class TopicsTransformer:
    def transform(self, topic_df):
        topic_df = topic_df.drop_duplicates(subset=["name"]).dropna()[
            ["name", "display_name", "description"]
        ]
        logger.info("Built %d topics", len(topic_df))
        return topic_df
