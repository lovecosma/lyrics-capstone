import pandas as pd
import pytest

from services.transformers import TrackGenreTransformer

TRACK_ID_COLUMN = "track_id"
GENRE_ID_COLUMN = "genre_id"
TITLE_COLUMN = "title"
TRACK_NAME_COLUMN = "track_name"
ARTIST_NAME_COLUMN = "artist_name"
GENRE_COLUMN = "genre"
GENRE_NAME_COLUMN = "name"
TITLE = "Old Town Road"
ARTIST_NAME = "Lil Nas X"
OTHER_ARTIST_NAME = "Billie Eilish"
GENRE = "country"
OTHER_GENRE = "dance"


@pytest.fixture
def transformer():
    return TrackGenreTransformer()


@pytest.fixture
def db_track_df():
    return pd.DataFrame(
        {TRACK_ID_COLUMN: [0], TITLE_COLUMN: [TITLE], ARTIST_NAME_COLUMN: [ARTIST_NAME]}
    )


@pytest.fixture
def db_genre_df():
    return pd.DataFrame({GENRE_ID_COLUMN: [0], GENRE_NAME_COLUMN: [GENRE]})


def source_track(artist_name=ARTIST_NAME, genre=GENRE):
    return {
        TRACK_NAME_COLUMN: TITLE,
        ARTIST_NAME_COLUMN: artist_name,
        GENRE_COLUMN: genre,
    }


def track_genres(transformer, db_track_df, db_genre_df, *source_tracks):
    return transformer.transform(
        db_track_df, db_genre_df, pd.DataFrame(source_tracks)
    )


class TestTransform:
    def test_links_a_track_to_its_genre(self, transformer, db_track_df, db_genre_df):
        track_genre_df = track_genres(
            transformer, db_track_df, db_genre_df, source_track()
        )

        assert track_genre_df.to_dict("records") == [
            {
                TRACK_ID_COLUMN: db_track_df[TRACK_ID_COLUMN].item(),
                GENRE_ID_COLUMN: db_genre_df[GENRE_ID_COLUMN].item(),
            }
        ]

    def test_matches_genres_regardless_of_formatting(
        self, transformer, db_track_df, db_genre_df
    ):
        track_genre_df = track_genres(
            transformer,
            db_track_df,
            db_genre_df,
            source_track(genre=f" {GENRE.upper()} "),
        )

        assert track_genre_df[GENRE_ID_COLUMN].tolist() == db_genre_df[
            GENRE_ID_COLUMN
        ].tolist()

    def test_links_a_track_once_when_it_charted_repeatedly(
        self, transformer, db_track_df, db_genre_df
    ):
        track_genre_df = track_genres(
            transformer, db_track_df, db_genre_df, source_track(), source_track()
        )

        assert track_genre_df[TRACK_ID_COLUMN].tolist() == db_track_df[
            TRACK_ID_COLUMN
        ].tolist()

    def test_skips_genres_missing_from_the_genre_table(
        self, transformer, db_track_df, db_genre_df
    ):
        assert track_genres(
            transformer, db_track_df, db_genre_df, source_track(genre=OTHER_GENRE)
        ).empty

    def test_ignores_the_same_title_by_another_artist(
        self, transformer, db_track_df, db_genre_df
    ):
        assert track_genres(
            transformer,
            db_track_df,
            db_genre_df,
            source_track(artist_name=OTHER_ARTIST_NAME),
        ).empty
