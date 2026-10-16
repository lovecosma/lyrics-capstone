import pandas as pd
import pytest

from transformers import TopicsTransformer

NAME_COLUMN = "name"
DISPLAY_NAME_COLUMN = "display_name"
DESCRIPTION_COLUMN = "description"
KEYWORDS_COLUMN = "keywords"
TOPIC_COLUMNS = [NAME_COLUMN, DISPLAY_NAME_COLUMN, DESCRIPTION_COLUMN]
NAME = "heartbreak"
DISPLAY_NAME = "Heartbreak"
OTHER_DISPLAY_NAME = "Broken Hearts"
DESCRIPTION = "Songs about the end of a relationship"
KEYWORDS = "breakup, goodbye"


@pytest.fixture
def transformer():
    return TopicsTransformer()


def topic(display_name=DISPLAY_NAME, description=DESCRIPTION):
    return {
        NAME_COLUMN: NAME,
        DISPLAY_NAME_COLUMN: display_name,
        DESCRIPTION_COLUMN: description,
        KEYWORDS_COLUMN: KEYWORDS,
    }


def topics(transformer, *topic_rows):
    return transformer.transform(pd.DataFrame(topic_rows))


class TestTransform:
    def test_keeps_the_first_topic_for_a_name(self, transformer):
        assert topics(transformer, topic(), topic(display_name=OTHER_DISPLAY_NAME))[
            DISPLAY_NAME_COLUMN
        ].tolist() == [DISPLAY_NAME]

    def test_skips_incomplete_topics(self, transformer):
        assert topics(transformer, topic(description=None)).empty

    def test_keeps_only_topic_columns(self, transformer):
        assert topics(transformer, topic()).columns.tolist() == TOPIC_COLUMNS
