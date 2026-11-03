import pandas as pd
import pytest

from services.transformers import WordEmotionTransformer

WORD_COLUMN = "word"
EMOTION_COLUMN = "emotion"
EMOTION_ID_COLUMN = "emotion_id"
EMOTION_NAME_COLUMN = "name"
WORD = "love"
EMOTION = "joy"
OTHER_EMOTION = "anger"


@pytest.fixture
def transformer():
    return WordEmotionTransformer()


@pytest.fixture
def db_emotion_df():
    return pd.DataFrame({EMOTION_ID_COLUMN: [0], EMOTION_NAME_COLUMN: [EMOTION]})


def word_emotion_df(emotion=EMOTION):
    return pd.DataFrame({WORD_COLUMN: [WORD], EMOTION_COLUMN: [emotion]})


class TestTransform:
    def test_links_words_to_their_emotions(self, transformer, db_emotion_df):
        assert transformer.transform(db_emotion_df, word_emotion_df()).to_dict(
            "records"
        ) == [
            {
                WORD_COLUMN: WORD,
                EMOTION_ID_COLUMN: db_emotion_df[EMOTION_ID_COLUMN].item(),
            }
        ]

    def test_skips_emotions_missing_from_the_emotion_table(
        self, transformer, db_emotion_df
    ):
        assert transformer.transform(
            db_emotion_df, word_emotion_df(OTHER_EMOTION)
        ).empty
