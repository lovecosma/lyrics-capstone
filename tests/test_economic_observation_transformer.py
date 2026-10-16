import pandas as pd
import pytest

from transformers import EconomicObservationTransformer

INDICATOR_ID_COLUMN = "economic_indicator_id"
CODE_COLUMN = "code"
OBSERVATION_DATE_COLUMN = "observation_date"
VALUE_COLUMN = "value"
CODE = "UNRATE"
OTHER_CODE = "CPIAUCSL"
OBSERVATION_DATE = "2019-01-01"
VALUE = 4.0


@pytest.fixture
def transformer():
    return EconomicObservationTransformer()


@pytest.fixture
def db_indicator_df():
    return pd.DataFrame({INDICATOR_ID_COLUMN: [0], CODE_COLUMN: [CODE]})


def observation_df(code=CODE, value=VALUE):
    return pd.DataFrame(
        {
            CODE_COLUMN: [code],
            OBSERVATION_DATE_COLUMN: [OBSERVATION_DATE],
            VALUE_COLUMN: [value],
        }
    )


class TestTransform:
    def test_links_observations_to_their_indicator(
        self, transformer, db_indicator_df
    ):
        assert transformer.transform(db_indicator_df, observation_df()).to_dict(
            "records"
        ) == [
            {
                INDICATOR_ID_COLUMN: db_indicator_df[INDICATOR_ID_COLUMN].item(),
                OBSERVATION_DATE_COLUMN: OBSERVATION_DATE,
                VALUE_COLUMN: VALUE,
            }
        ]

    def test_skips_observations_without_a_value(self, transformer, db_indicator_df):
        assert transformer.transform(
            db_indicator_df, observation_df(value=None)
        ).empty

    def test_skips_observations_of_unknown_indicators(
        self, transformer, db_indicator_df
    ):
        assert transformer.transform(
            db_indicator_df, observation_df(code=OTHER_CODE)
        ).empty
