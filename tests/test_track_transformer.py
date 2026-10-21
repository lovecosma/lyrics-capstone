import pandas as pd
import pytest

from services.transformers import TrackTransformer

TRACK_NAME_COLUMN, ARTIST_NAME_COLUMN = TrackTransformer.SONG_KEY_COLUMNS
TITLE_COLUMN = TrackTransformer.COLUMN_RENAMES[TRACK_NAME_COLUMN]
LYRICS_COLUMN = "lyrics"
KEY_COLUMN = "key"
GENRE_COLUMN = "genre"
SOURCE_COLUMN_NAMES = {
    title: source for source, title in TrackTransformer.COLUMN_RENAMES.items()
}
SOURCE_TRACK_COLUMNS = [
    SOURCE_COLUMN_NAMES.get(column, column) for column in TrackTransformer.TRACK_COLUMNS
]
TRACK_NAME = "Old Town Road"
OTHER_TRACK_NAME = "Bad Guy"
ARTIST_NAME = "Lil Nas X"
OTHER_ARTIST_NAME = "Billie Eilish"
LYRICS = "I'm gonna take my horse to the old town road"
OTHER_LYRICS = "So you're a tough guy"
GENRE = "country"
AUDIO_FEATURE = 0.5
INTEGER_FEATURE = 1
CHART_YEAR = 2019
LATER_CHART_YEAR = CHART_YEAR + 1


@pytest.fixture
def transformer():
    return TrackTransformer()


def source_track(**overrides):
    return {
        **dict.fromkeys(SOURCE_TRACK_COLUMNS, AUDIO_FEATURE),
        **dict.fromkeys(TrackTransformer.INTEGER_COLUMNS, INTEGER_FEATURE),
        TRACK_NAME_COLUMN: TRACK_NAME,
        ARTIST_NAME_COLUMN: ARTIST_NAME,
        LYRICS_COLUMN: LYRICS,
        TrackTransformer.CHART_YEAR_COLUMN: CHART_YEAR,
        **overrides,
    }


def tracks(transformer, *source_tracks):
    return transformer.transform(pd.DataFrame(source_tracks))


class TestTransform:
    def test_keeps_one_track_per_song(self, transformer):
        track_df = tracks(
            transformer,
            source_track(),
            source_track(**{TrackTransformer.CHART_YEAR_COLUMN: LATER_CHART_YEAR}),
        )

        assert track_df[TITLE_COLUMN].tolist() == [TRACK_NAME]

    def test_keeps_a_track_for_each_song(self, transformer):
        track_df = tracks(
            transformer,
            source_track(),
            source_track(**{TRACK_NAME_COLUMN: OTHER_TRACK_NAME}),
        )

        assert track_df[TITLE_COLUMN].tolist() == [TRACK_NAME, OTHER_TRACK_NAME]

    def test_treats_the_same_title_by_another_artist_as_another_song(
        self, transformer
    ):
        track_df = tracks(
            transformer,
            source_track(),
            source_track(**{ARTIST_NAME_COLUMN: OTHER_ARTIST_NAME}),
        )

        assert track_df[ARTIST_NAME_COLUMN].tolist() == [
            ARTIST_NAME,
            OTHER_ARTIST_NAME,
        ]

    def test_keeps_the_earliest_charting_row_of_a_song(self, transformer):
        track_df = tracks(
            transformer,
            source_track(
                **{
                    TrackTransformer.CHART_YEAR_COLUMN: LATER_CHART_YEAR,
                    LYRICS_COLUMN: OTHER_LYRICS,
                }
            ),
            source_track(),
        )

        assert track_df[LYRICS_COLUMN].tolist() == [LYRICS]

    def test_keeps_only_track_columns(self, transformer):
        track_df = tracks(transformer, source_track(**{GENRE_COLUMN: GENRE}))

        assert track_df.columns.tolist() == list(TrackTransformer.TRACK_COLUMNS)

    def test_stores_integer_columns_as_nullable_integers(self, transformer):
        track_df = tracks(
            transformer,
            source_track(),
            source_track(**{TRACK_NAME_COLUMN: OTHER_TRACK_NAME, KEY_COLUMN: None}),
        )

        assert (
            track_df.dtypes[list(TrackTransformer.INTEGER_COLUMNS)]
            == TrackTransformer.NULLABLE_INTEGER_DTYPE
        ).all()
