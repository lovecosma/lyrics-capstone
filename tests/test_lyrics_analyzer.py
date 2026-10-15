import pandas as pd
import pytest
from lyrics_helpers import song

from lyrics_analysis import LyricsAnalyzer

TRACK_ID = 1
OTHER_TRACK_ID = 2
REPEAT_COUNT = 3
WORDS = ["midnight", "city", "lights", "city"]
VARIED_LYRICS = (
    "city lights shine on every street tonight while we dance under neon skies"
)
NON_CONTENT_WORDS = {"in", "the", "oh", "yeah"}


@pytest.fixture
def analyzer():
    return LyricsAnalyzer(NON_CONTENT_WORDS)


def track_df(lyrics_by_track_id):
    return pd.DataFrame(
        {
            LyricsAnalyzer.TRACK_ID_COLUMN: list(lyrics_by_track_id),
            LyricsAnalyzer.LYRICS_COLUMN: list(lyrics_by_track_id.values()),
        }
    )


def metrics_for(analyzer, lyrics):
    lyrics_metric_df, _ = analyzer.analyze(track_df({TRACK_ID: lyrics}))
    return lyrics_metric_df.iloc[0]


def ngrams_for(analyzer, lyrics):
    _, lyrics_ngram_metric_df = analyzer.analyze(track_df({TRACK_ID: lyrics}))
    return lyrics_ngram_metric_df


def phrases_in(analyzer, lyrics):
    return set(ngrams_for(analyzer, lyrics)["ngram"])


class TestWordCounts:
    def test_counts_every_word(self, analyzer):
        assert metrics_for(analyzer, " ".join(WORDS)).word_count == len(WORDS)

    def test_counts_each_distinct_word_once(self, analyzer):
        assert metrics_for(analyzer, " ".join(WORDS)).unique_word_count == len(
            set(WORDS)
        )

    def test_skips_section_headers(self, analyzer):
        with_header = metrics_for(
            analyzer, song(VARIED_LYRICS, "Chorus:", VARIED_LYRICS)
        )

        assert (
            with_header.word_count
            == metrics_for(analyzer, song(VARIED_LYRICS, VARIED_LYRICS)).word_count
        )


class TestWordMeasures:
    def test_measures_average_word_length(self, analyzer):
        expected_average = sum(map(len, WORDS)) / len(WORDS)

        assert (
            metrics_for(analyzer, " ".join(WORDS)).average_word_length
            == expected_average
        )

    def test_scores_varied_lyrics_as_more_diverse_than_repetitive_lyrics(
        self, analyzer
    ):
        repetitive_lyrics = " ".join(["baby"] * len(VARIED_LYRICS.split()))

        assert (
            metrics_for(analyzer, VARIED_LYRICS).lexical_diversity
            > metrics_for(analyzer, repetitive_lyrics).lexical_diversity
        )

    def test_has_no_lexical_diversity_without_words(self, analyzer):
        assert pd.isna(metrics_for(analyzer, "Chorus").lexical_diversity)

    def test_has_no_average_word_length_without_words(self, analyzer):
        assert pd.isna(metrics_for(analyzer, "Chorus").average_word_length)


class TestMetricRows:
    def test_returns_one_row_per_track(self, analyzer):
        lyrics_by_track_id = {TRACK_ID: VARIED_LYRICS, OTHER_TRACK_ID: VARIED_LYRICS}
        lyrics_metric_df, _ = analyzer.analyze(track_df(lyrics_by_track_id))

        assert lyrics_metric_df[LyricsAnalyzer.TRACK_ID_COLUMN].tolist() == list(
            lyrics_by_track_id
        )

    def test_tags_rows_with_the_analysis_version(self, analyzer):
        assert (
            metrics_for(analyzer, VARIED_LYRICS).analysis_version
            == LyricsAnalyzer.ANALYSIS_VERSION
        )


class TestPhrases:
    def test_includes_one_two_and_three_word_phrases(self, analyzer):
        expected_phrases = {"midnight", "midnight city", "midnight city lights"}

        assert expected_phrases <= phrases_in(analyzer, "midnight city lights")

    def test_lowercases_phrases(self, analyzer):
        assert "midnight city" in phrases_in(analyzer, "Midnight City")

    def test_never_builds_phrases_across_lines(self, analyzer):
        assert "city lights" not in phrases_in(
            analyzer, song("midnight city", "lights out")
        )

    def test_counts_how_often_a_phrase_repeats(self, analyzer):
        repeated_line = "midnight city"
        ngram_df = ngrams_for(analyzer, song(*[repeated_line] * REPEAT_COUNT))

        assert (
            ngram_df.set_index("ngram").loc[repeated_line, "frequency"] == REPEAT_COUNT
        )

    def test_records_how_many_words_each_phrase_has(self, analyzer):
        ngram_df = ngrams_for(analyzer, VARIED_LYRICS)

        assert ngram_df["n"].equals(ngram_df["ngram"].str.split().str.len())

    def test_tags_phrases_with_the_analysis_version(self, analyzer):
        ngram_df = ngrams_for(analyzer, VARIED_LYRICS)

        assert ngram_df["analysis_version"].eq(LyricsAnalyzer.ANALYSIS_VERSION).all()

    def test_tags_phrases_with_their_track(self, analyzer):
        lyrics_by_track_id = {TRACK_ID: "midnight city", OTHER_TRACK_ID: "neon skies"}
        _, lyrics_ngram_metric_df = analyzer.analyze(track_df(lyrics_by_track_id))
        phrase_track_ids = lyrics_ngram_metric_df.set_index("ngram")[
            LyricsAnalyzer.TRACK_ID_COLUMN
        ]

        assert phrase_track_ids["neon skies"] == OTHER_TRACK_ID


class TestNonContentWords:
    def test_drops_non_content_words_on_their_own(self, analyzer):
        assert "the" not in phrases_in(analyzer, "in the club")

    def test_drops_phrases_made_only_of_non_content_words(self, analyzer):
        assert "oh yeah" not in phrases_in(analyzer, "oh yeah midnight city")

    def test_keeps_phrases_with_at_least_one_content_word(self, analyzer):
        assert "the club" in phrases_in(analyzer, "in the club")

    def test_keeps_words_that_were_not_passed_in_as_non_content(self):
        assert "the" in phrases_in(LyricsAnalyzer(set()), "in the club")
