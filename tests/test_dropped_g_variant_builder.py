import pandas as pd
import pytest

from transformers import DroppedGVariantBuilder

WORD_COLUMN = "word"
EMOTION_COLUMN = "emotion"
EMOTION = "joy"
GERUND = "loving"
DROPPED_G_VARIANT = "lovin"
NON_GERUND = "love"
ONE_SYLLABLE_WORD = "sing"


@pytest.fixture
def builder():
    return DroppedGVariantBuilder()


def variants(builder, *words, lexicon_words=frozenset()):
    lexicon_df = pd.DataFrame({WORD_COLUMN: words, EMOTION_COLUMN: EMOTION})
    return builder.build(lexicon_df, WORD_COLUMN, frozenset(words) | lexicon_words)


class TestBuild:
    def test_adds_the_dropped_g_spelling_of_a_gerund(self, builder):
        assert variants(builder, GERUND)[WORD_COLUMN].tolist() == [DROPPED_G_VARIANT]

    def test_keeps_the_rest_of_the_gerunds_row(self, builder):
        assert variants(builder, GERUND)[EMOTION_COLUMN].tolist() == [EMOTION]

    def test_skips_words_that_are_not_gerunds(self, builder):
        assert variants(builder, NON_GERUND).empty

    def test_skips_one_syllable_words_ending_in_ing(self, builder):
        assert variants(builder, ONE_SYLLABLE_WORD).empty

    def test_skips_variants_already_in_the_lexicon(self, builder):
        assert variants(
            builder, GERUND, lexicon_words=frozenset({DROPPED_G_VARIANT})
        ).empty
