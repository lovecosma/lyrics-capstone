import pandas as pd
from fake_variant_builder import FakeVariantBuilder

from services.transformers import EmotionLexiconTransformer

WORD_COLUMN = EmotionLexiconTransformer.WORD_COLUMN
EMOTION_COLUMN = EmotionLexiconTransformer.EMOTION_COLUMN
ASSOCIATION_COLUMN = EmotionLexiconTransformer.ASSOCIATION_COLUMN
NOT_ASSOCIATED = 0
WORD = "love"
OTHER_WORD = "hate"
VARIANT_WORD = "lovin"
EMOTION = "joy"


def lexicon_row(
    word=WORD, emotion=EMOTION, association=EmotionLexiconTransformer.ASSOCIATED
):
    return {
        WORD_COLUMN: word,
        EMOTION_COLUMN: emotion,
        ASSOCIATION_COLUMN: association,
    }


def word_emotions(*lexicon_rows, variant_builder=None):
    transformer = EmotionLexiconTransformer(variant_builder or FakeVariantBuilder())
    lexicon_df = pd.DataFrame(
        lexicon_rows, columns=list(EmotionLexiconTransformer.LEXICON_COLUMNS)
    )
    return transformer.transform(lexicon_df)


def word_emotion_df(*words):
    return pd.DataFrame({WORD_COLUMN: words, EMOTION_COLUMN: EMOTION})


class TestTransform:
    def test_keeps_associated_words(self):
        assert word_emotions(lexicon_row())[WORD_COLUMN].tolist() == [WORD]

    def test_skips_unassociated_words(self):
        assert word_emotions(lexicon_row(association=NOT_ASSOCIATED)).empty

    def test_skips_rows_without_an_emotion(self):
        assert word_emotions(lexicon_row(emotion=None)).empty

    def test_normalizes_words(self):
        assert word_emotions(lexicon_row(word=f" {WORD.upper()} "))[
            WORD_COLUMN
        ].tolist() == [WORD]

    def test_strips_emotions(self):
        assert word_emotions(lexicon_row(emotion=f" {EMOTION} "))[
            EMOTION_COLUMN
        ].tolist() == [EMOTION]

    def test_keeps_only_words_and_emotions(self):
        assert word_emotions(lexicon_row()).columns.tolist() == [
            WORD_COLUMN,
            EMOTION_COLUMN,
        ]

    def test_adds_variant_spellings(self):
        variant_builder = FakeVariantBuilder(word_emotion_df(VARIANT_WORD))

        assert word_emotions(lexicon_row(), variant_builder=variant_builder)[
            WORD_COLUMN
        ].tolist() == [WORD, VARIANT_WORD]

    def test_checks_variants_against_every_lexicon_word(self):
        variant_builder = FakeVariantBuilder()
        word_emotions(
            lexicon_row(),
            lexicon_row(word=OTHER_WORD, association=NOT_ASSOCIATED),
            variant_builder=variant_builder,
        )

        assert variant_builder.lexicon_words == frozenset({WORD, OTHER_WORD})

    def test_drops_duplicate_word_emotions(self):
        variant_builder = FakeVariantBuilder(word_emotion_df(WORD))

        assert word_emotions(lexicon_row(), variant_builder=variant_builder)[
            WORD_COLUMN
        ].tolist() == [WORD]
