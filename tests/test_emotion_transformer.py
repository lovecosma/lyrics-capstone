import pandas as pd
import pytest

from transformers import EmotionTransformer

EMOTION_COLUMN = "emotion"
NAME_COLUMN = "name"
DISPLAY_NAME_COLUMN = "display_name"
EMOTION = "joy"
OTHER_EMOTION = "anger"


@pytest.fixture
def transformer():
    return EmotionTransformer()


def emotions(transformer, *emotion_names):
    return transformer.transform(pd.DataFrame({EMOTION_COLUMN: emotion_names}))


class TestTransform:
    def test_builds_one_emotion_per_distinct_emotion_in_order(self, transformer):
        assert emotions(transformer, EMOTION, OTHER_EMOTION, EMOTION)[
            NAME_COLUMN
        ].tolist() == sorted({EMOTION, OTHER_EMOTION})

    def test_title_cases_display_names(self, transformer):
        assert emotions(transformer, EMOTION)[DISPLAY_NAME_COLUMN].tolist() == [
            EMOTION.title()
        ]
