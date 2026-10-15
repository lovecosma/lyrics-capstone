import pytest
from lyrics_helpers import song

from lyrics_analysis import LyricsTokenizer

FIRST_LINE = "midnight city"
SECOND_LINE = "neon skies"


@pytest.fixture
def tokenizer():
    return LyricsTokenizer()


def test_splits_lyrics_into_lines_of_words(tokenizer):
    lines = [FIRST_LINE, SECOND_LINE]

    assert tokenizer.tokenize(song(*lines)) == [line.split() for line in lines]


def test_skips_blank_lines(tokenizer):
    with_blank_line = song(FIRST_LINE, "", SECOND_LINE)

    assert tokenizer.tokenize(with_blank_line) == tokenizer.tokenize(
        song(FIRST_LINE, SECOND_LINE)
    )


def test_lowercases_words(tokenizer):
    assert tokenizer.tokenize("Midnight CITY") == tokenizer.tokenize(FIRST_LINE)


def test_drops_punctuation(tokenizer):
    assert tokenizer.tokenize("midnight, city!") == tokenizer.tokenize(FIRST_LINE)


def test_keeps_contractions_as_one_word(tokenizer):
    contraction_line = "don't stop"

    assert tokenizer.tokenize(contraction_line) == [contraction_line.split()]


def test_straightens_curly_apostrophes(tokenizer):
    assert tokenizer.tokenize("don\u2019t stop") == tokenizer.tokenize("don't stop")


def test_removes_zero_width_spaces(tokenizer):
    assert tokenizer.tokenize("mid\u200bnight city") == tokenizer.tokenize(FIRST_LINE)
