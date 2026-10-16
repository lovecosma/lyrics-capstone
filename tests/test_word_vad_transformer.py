import pandas as pd
from fake_variant_builder import FakeVariantBuilder

from transformers import WordVadTransformer

WORD_COLUMN = WordVadTransformer.WORD_COLUMN
VALENCE_COLUMN = WordVadTransformer.VALENCE_COLUMN
LEXICON_COLUMNS = list(WordVadTransformer.LEXICON_COLUMNS)
SCORE_COLUMNS = [column for column in LEXICON_COLUMNS if column != WORD_COLUMN]
WORD = "love"
VARIANT_WORD = "lovin"
SCORE = 0.5
OTHER_SCORE = SCORE / 2


def vad_row(word=WORD, valence=SCORE):
    return {
        **dict.fromkeys(SCORE_COLUMNS, SCORE),
        WORD_COLUMN: word,
        VALENCE_COLUMN: valence,
    }


def vad_df(*vad_rows, columns=LEXICON_COLUMNS):
    return pd.DataFrame(vad_rows, columns=columns)


def word_vads(*vad_rows, variant_builder=None, columns=LEXICON_COLUMNS):
    transformer = WordVadTransformer(variant_builder or FakeVariantBuilder())
    return transformer.transform(vad_df(*vad_rows, columns=columns))


class TestTransform:
    def test_normalizes_words(self):
        assert word_vads(vad_row(word=f" {WORD.upper()} "))[
            WORD_COLUMN
        ].tolist() == [WORD]

    def test_skips_words_missing_a_score(self):
        assert word_vads(vad_row(valence=None)).empty

    def test_keeps_the_first_score_of_a_repeated_word(self):
        assert word_vads(vad_row(), vad_row(word=WORD.upper(), valence=OTHER_SCORE))[
            VALENCE_COLUMN
        ].tolist() == [SCORE]

    def test_adds_variant_spellings(self):
        variant_builder = FakeVariantBuilder(vad_df(vad_row(word=VARIANT_WORD)))

        assert word_vads(vad_row(), variant_builder=variant_builder)[
            WORD_COLUMN
        ].tolist() == [WORD, VARIANT_WORD]

    def test_checks_variants_against_the_normalized_words(self):
        variant_builder = FakeVariantBuilder()
        word_vads(vad_row(word=WORD.upper()), variant_builder=variant_builder)

        assert variant_builder.lexicon_words == frozenset({WORD})

    def test_orders_columns_as_the_lexicon_columns(self):
        assert (
            word_vads(vad_row(), columns=LEXICON_COLUMNS[::-1]).columns.tolist()
            == LEXICON_COLUMNS
        )
