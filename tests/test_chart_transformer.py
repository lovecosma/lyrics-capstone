import pandas as pd
import pytest

from transformers import ChartTransformer

CHART_YEAR_COLUMN = "chart_year"
YEAR_COLUMN = "year"
CHART_YEAR = 2019
LATER_CHART_YEAR = CHART_YEAR + 1


@pytest.fixture
def transformer():
    return ChartTransformer()


def chart_years(transformer, *chart_years):
    track_df = pd.DataFrame({CHART_YEAR_COLUMN: chart_years})
    return transformer.transform(track_df)[YEAR_COLUMN]


class TestTransform:
    def test_builds_one_chart_per_distinct_year(self, transformer):
        assert chart_years(
            transformer, CHART_YEAR, LATER_CHART_YEAR, CHART_YEAR
        ).tolist() == [CHART_YEAR, LATER_CHART_YEAR]

    def test_skips_tracks_without_a_chart_year(self, transformer):
        assert chart_years(transformer, CHART_YEAR, None).tolist() == [CHART_YEAR]

    def test_stores_years_as_integers(self, transformer):
        assert pd.api.types.is_integer_dtype(
            chart_years(transformer, CHART_YEAR, None)
        )
