import pandas as pd

from genre_enrichment import TrackGenreEnricher

TITLE = "First Person Shooter"
ARTIST_NAME = "Drake"
FEATURED_ARTIST_NAME = f"{ARTIST_NAME} feat. J. Cole"
OTHER_ARTIST_NAME = "Karaoke Freaks"
HIP_HOP_GENRE = "Hip-Hop/Rap"
NORMALIZED_HIP_HOP_GENRE = HIP_HOP_GENRE.lower()
LOADED_GENRE = "hip-hop"
RELEASE_DATE = "2023-10-06T12:00:00Z"
TRACK_ID_COLUMN = TrackGenreEnricher.TRACK_ID_COLUMN
GENRE_COLUMN = TrackGenreEnricher.GENRE_COLUMN
GENRE_NAME_COLUMN = TrackGenreEnricher.GENRE_NAME_COLUMN
GENRE_ID_COLUMN = "genre_id"


class FakeITunesClient:
    def __init__(self, results):
        self._results = results

    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        pass

    def search_songs(self, _title, _artist_name):
        return self._results


def enricher(*results):
    return TrackGenreEnricher(lambda: FakeITunesClient(results))


def track_df(artist_name=ARTIST_NAME):
    return pd.DataFrame(
        {
            TRACK_ID_COLUMN: [0],
            TrackGenreEnricher.TITLE_COLUMN: [TITLE],
            TrackGenreEnricher.ARTIST_NAME_COLUMN: [artist_name],
            TrackGenreEnricher.GENRE_SEARCHED_AT_COLUMN: [None],
        }
    )


def genre_df(*genre_names):
    return pd.DataFrame(
        {
            GENRE_ID_COLUMN: range(len(genre_names)),
            GENRE_NAME_COLUMN: genre_names,
        }
    )


def itunes_result(track_name=TITLE, artist_name=ARTIST_NAME, genre=HIP_HOP_GENRE):
    return {
        TrackGenreEnricher.ITUNES_TRACK_NAME_FIELD: track_name,
        TrackGenreEnricher.ITUNES_ARTIST_NAME_FIELD: artist_name,
        TrackGenreEnricher.ITUNES_GENRE_FIELD: genre,
        TrackGenreEnricher.ITUNES_RELEASE_DATE_FIELD: RELEASE_DATE,
    }


def enriched_genres(db_track_df, *results):
    source_track_df = enricher(*results).enrich(db_track_df).source_track_df
    return dict(
        zip(source_track_df[TRACK_ID_COLUMN], source_track_df[GENRE_COLUMN])
    )


def only_track_id(db_track_df):
    return db_track_df[TRACK_ID_COLUMN].item()


class TestEnrich:
    def test_keeps_the_matched_songs_itunes_genre(self):
        db_track_df = track_df()

        assert enriched_genres(db_track_df, itunes_result()) == {
            only_track_id(db_track_df): HIP_HOP_GENRE
        }

    def test_matches_a_featured_credit_in_the_itunes_title(self):
        db_track_df = track_df(FEATURED_ARTIST_NAME)
        featured_result = itunes_result(f"{TITLE} (feat. J. Cole)")

        assert enriched_genres(db_track_df, featured_result) == {
            only_track_id(db_track_df): HIP_HOP_GENRE
        }

    def test_ignores_songs_by_another_artist(self):
        cover = itunes_result(artist_name=OTHER_ARTIST_NAME)

        assert enriched_genres(track_df(), cover) == {}

    def test_skips_tracks_without_search_results(self):
        assert enriched_genres(track_df()) == {}


class TestSelectNewGenres:
    def test_returns_found_genres_missing_from_the_genre_table(self):
        source_track_df = enricher(itunes_result()).enrich(track_df()).source_track_df

        new_genre_df = enricher().select_new_genres(
            source_track_df, genre_df(LOADED_GENRE)
        )

        assert new_genre_df[GENRE_NAME_COLUMN].tolist() == [NORMALIZED_HIP_HOP_GENRE]

    def test_skips_genres_already_in_the_genre_table(self):
        source_track_df = enricher(itunes_result()).enrich(track_df()).source_track_df

        new_genre_df = enricher().select_new_genres(
            source_track_df, genre_df(NORMALIZED_HIP_HOP_GENRE)
        )

        assert new_genre_df.empty


class TestSelectMissing:
    def test_excludes_tracks_that_have_a_genre(self):
        db_track_df = track_df()
        track_genre_df = pd.DataFrame(
            {
                TRACK_ID_COLUMN: db_track_df[TRACK_ID_COLUMN],
                GENRE_ID_COLUMN: genre_df(LOADED_GENRE)[GENRE_ID_COLUMN],
            }
        )

        assert enricher().select_missing(db_track_df, track_genre_df).empty
