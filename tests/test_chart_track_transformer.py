import pandas as pd
import pytest

from transformers import ChartTrackTransformer

TRACK_ID_COLUMN = "track_id"
CHART_ID_COLUMN = "chart_id"
TITLE_COLUMN = "title"
TRACK_NAME_COLUMN = "track_name"
ARTIST_NAME_COLUMN = "artist_name"
CHART_YEAR_COLUMN = "chart_year"
YEAR_COLUMN = "year"
RANK_COLUMN = "rank"
TITLE = "Old Town Road"
ARTIST_NAME = "Lil Nas X"
OTHER_ARTIST_NAME = "Billie Eilish"
CHART_YEAR = 2019
LATER_CHART_YEAR = CHART_YEAR + 1
RANK = 1


@pytest.fixture
def transformer():
    return ChartTrackTransformer()


@pytest.fixture
def db_track_df():
    return pd.DataFrame(
        {TRACK_ID_COLUMN: [0], TITLE_COLUMN: [TITLE], ARTIST_NAME_COLUMN: [ARTIST_NAME]}
    )


def db_chart_df(*years):
    return pd.DataFrame({CHART_ID_COLUMN: range(len(years)), YEAR_COLUMN: years})


def source_track(artist_name=ARTIST_NAME, chart_year=CHART_YEAR):
    return {
        TRACK_NAME_COLUMN: TITLE,
        ARTIST_NAME_COLUMN: artist_name,
        CHART_YEAR_COLUMN: chart_year,
        RANK_COLUMN: RANK,
    }


def chart_tracks(transformer, db_track_df, db_chart_df, *source_tracks):
    return transformer.transform(
        db_track_df, db_chart_df, pd.DataFrame(source_tracks)
    )


class TestTransform:
    def test_links_a_track_to_its_chart_with_its_rank(
        self, transformer, db_track_df
    ):
        chart_df = db_chart_df(CHART_YEAR)

        assert chart_tracks(
            transformer, db_track_df, chart_df, source_track()
        ).to_dict("records") == [
            {
                TRACK_ID_COLUMN: db_track_df[TRACK_ID_COLUMN].item(),
                CHART_ID_COLUMN: chart_df[CHART_ID_COLUMN].item(),
                RANK_COLUMN: RANK,
            }
        ]

    def test_links_a_track_to_every_chart_it_appeared_on(
        self, transformer, db_track_df
    ):
        chart_df = db_chart_df(CHART_YEAR, LATER_CHART_YEAR)
        chart_track_df = chart_tracks(
            transformer,
            db_track_df,
            chart_df,
            source_track(),
            source_track(chart_year=LATER_CHART_YEAR),
        )

        assert chart_track_df[CHART_ID_COLUMN].tolist() == chart_df[
            CHART_ID_COLUMN
        ].tolist()

    def test_links_a_chart_entry_once(self, transformer, db_track_df):
        chart_track_df = chart_tracks(
            transformer,
            db_track_df,
            db_chart_df(CHART_YEAR),
            source_track(),
            source_track(),
        )

        assert chart_track_df[TRACK_ID_COLUMN].tolist() == db_track_df[
            TRACK_ID_COLUMN
        ].tolist()

    def test_skips_years_without_a_chart(self, transformer, db_track_df):
        assert chart_tracks(
            transformer, db_track_df, db_chart_df(LATER_CHART_YEAR), source_track()
        ).empty

    def test_ignores_the_same_title_by_another_artist(
        self, transformer, db_track_df
    ):
        assert chart_tracks(
            transformer,
            db_track_df,
            db_chart_df(CHART_YEAR),
            source_track(artist_name=OTHER_ARTIST_NAME),
        ).empty
