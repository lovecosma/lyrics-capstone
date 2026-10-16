import pandas as pd
import pytest

from transformers import EconomicIndicatorTransformer

CODE_COLUMN = "code"
DISPLAY_NAME_COLUMN = "display_name"
UNIT_COLUMN = "unit"
DESCRIPTION_COLUMN = "description"
SOURCE_COLUMN = "source"
INDICATOR_COLUMNS = [CODE_COLUMN, DISPLAY_NAME_COLUMN, UNIT_COLUMN, DESCRIPTION_COLUMN]
CODE = "UNRATE"
DISPLAY_NAME = "Unemployment Rate"
OTHER_DISPLAY_NAME = "Civilian Unemployment Rate"
UNIT = "percent"
DESCRIPTION = "Share of the labor force that is unemployed"
SOURCE = "FRED"


@pytest.fixture
def transformer():
    return EconomicIndicatorTransformer()


def indicator(display_name=DISPLAY_NAME, unit=UNIT):
    return {
        CODE_COLUMN: CODE,
        DISPLAY_NAME_COLUMN: display_name,
        UNIT_COLUMN: unit,
        DESCRIPTION_COLUMN: DESCRIPTION,
        SOURCE_COLUMN: SOURCE,
    }


def indicators(transformer, *indicator_rows):
    return transformer.transform(pd.DataFrame(indicator_rows))


class TestTransform:
    def test_keeps_the_first_indicator_for_a_code(self, transformer):
        assert indicators(
            transformer, indicator(), indicator(display_name=OTHER_DISPLAY_NAME)
        )[DISPLAY_NAME_COLUMN].tolist() == [DISPLAY_NAME]

    def test_skips_incomplete_indicators(self, transformer):
        assert indicators(transformer, indicator(unit=None)).empty

    def test_keeps_only_indicator_columns(self, transformer):
        assert (
            indicators(transformer, indicator()).columns.tolist() == INDICATOR_COLUMNS
        )
