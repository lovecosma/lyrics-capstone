import logging
import re

import pandas as pd
from lexicalrichness import LexicalRichness
from nltk import FreqDist
from nltk.tokenize import RegexpTokenizer
from nltk.util import everygrams

logger = logging.getLogger(__name__)


class LyricsAnalyzer:
    ANALYSIS_VERSION = "v3"
    MIN_NGRAM_SIZE = 1
    MAX_NGRAM_SIZE = 3
    NGRAM_SEPARATOR = " "
    CHARACTER_NORMALIZATION = str.maketrans(
        {"\u2019": "'", "\u2018": "'", "\u200b": None}
    )
    WORD_TOKENIZER = RegexpTokenizer(r"[^\W_]+(?:'[^\W_]+)*")
    SCRAPE_ARTIFACT_PATTERN = re.compile(
        r"^\s*\d+ Contributors?.*?Lyrics"
        r"|See .+? LiveGet tickets as low as \$\d+"
        r"|You might also like"
        r"|Embed\s*$"
    )
    SECTION_NAME = r"(?:verse|chorus|hook|bridge|intro|outro|pre-chorus|refrain)"
    SECTION_HEADER_PATTERN = re.compile(
        r"^[ \t]*(?:"
        # {Chorus}, (Chorus 16X), [Hook - 112 (Q)
        rf"[\[({{][ \t]*{SECTION_NAME}(?:[ \t]*(?:\d|x\d|[-:])[^\])}}\n]*)?[\])}}]?"
        # -CHORUS-
        rf"|-+[ \t]*{SECTION_NAME}(?:[ \t]*\d+)?[ \t]*-+"
        # Verse 1:, Chorus x2, Chorus until end
        rf"|{SECTION_NAME}(?:[ \t]*\d+)?[ \t]*:?(?:[ \t]+(?:\d+x|x\d+|until end|repeat))?"
        r")[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    SCRAPE_ARTIFACT_REPLACEMENT = "\n"
    SECTION_HEADER_REPLACEMENT = ""
    NON_CONTENT_WORD_PATHS = (
        "data/stopwords.txt",
        "data/lyric_stopwords.txt",
        "data/filler_words.txt",
    )
    COMMENT_PREFIX = "#"
    TRACK_ID_COLUMN = "track_id"
    LYRICS_COLUMN = "lyrics"
    WORD_COUNT_COLUMN = "word_count"
    LYRICS_NGRAM_METRIC_COLUMNS = (
        TRACK_ID_COLUMN,
        "ngram",
        "n",
        "frequency",
        "analysis_version",
    )

    def __init__(self):
        self._non_content_words = frozenset().union(
            *map(self._load_word_list, self.NON_CONTENT_WORD_PATHS)
        )

    def analyze(self, track_df):
        logger.info("Analyzing lyrics for %d tracks", len(track_df))
        lyrics_metrics = []
        lyrics_ngram_metrics = []
        for track_id, lyrics in zip(
            track_df[self.TRACK_ID_COLUMN], track_df[self.LYRICS_COLUMN]
        ):
            lines = self._tokenize_lines(self._clean_lyrics(lyrics))
            lyrics_metrics.append(self._compute_lyrics_metric(track_id, lines))
            lyrics_ngram_metrics.extend(
                self._compute_lyrics_ngram_metrics(track_id, lines)
            )

        lyrics_metric_df = pd.DataFrame(lyrics_metrics)
        wordless_track_count = lyrics_metric_df[self.WORD_COUNT_COLUMN].eq(0).sum()
        if wordless_track_count:
            logger.warning(
                "%d tracks have no words after cleaning lyrics", wordless_track_count
            )
        lyrics_ngram_metric_df = pd.DataFrame(
            lyrics_ngram_metrics, columns=list(self.LYRICS_NGRAM_METRIC_COLUMNS)
        )
        logger.info(
            "Computed %d lyrics metrics and %d n-gram metrics",
            len(lyrics_metric_df),
            len(lyrics_ngram_metric_df),
        )
        return lyrics_metric_df, lyrics_ngram_metric_df

    def _load_word_list(self, path):
        with open(path, encoding="utf-8") as word_list_file:
            lines = (line.strip() for line in word_list_file)
            return frozenset(
                line for line in lines if line and not line.startswith(self.COMMENT_PREFIX)
            )

    def _clean_lyrics(self, lyrics):
        without_artifacts = self.SCRAPE_ARTIFACT_PATTERN.sub(
            self.SCRAPE_ARTIFACT_REPLACEMENT, lyrics
        )
        return self.SECTION_HEADER_PATTERN.sub(
            self.SECTION_HEADER_REPLACEMENT, without_artifacts
        )

    def _tokenize_lines(self, lyrics):
        normalized = lyrics.translate(self.CHARACTER_NORMALIZATION).casefold()
        lines = (self.WORD_TOKENIZER.tokenize(line) for line in normalized.splitlines())
        return [line for line in lines if line]

    def _is_content_gram(self, gram):
        return not all(word in self._non_content_words for word in gram)

    def _compute_lyrics_metric(self, track_id, lines):
        words = [word for line in lines for word in line]
        word_frequencies = FreqDist(words)
        word_count = word_frequencies.N()
        return {
            self.TRACK_ID_COLUMN: track_id,
            self.WORD_COUNT_COLUMN: word_count,
            "unique_word_count": word_frequencies.B(),
            "lexical_diversity": (
                LexicalRichness(words, preprocessor=None, tokenizer=None).mtld()
                if word_count
                else None
            ),
            "average_word_length": (
                sum(
                    len(word) * frequency
                    for word, frequency in word_frequencies.items()
                )
                / word_count
                if word_count
                else None
            ),
            "analysis_version": self.ANALYSIS_VERSION,
        }

    def _compute_lyrics_ngram_metrics(self, track_id, lines):
        ngram_frequencies = FreqDist(
            gram
            for line in lines
            for gram in everygrams(line, self.MIN_NGRAM_SIZE, self.MAX_NGRAM_SIZE)
        )
        return (
            (
                track_id,
                self.NGRAM_SEPARATOR.join(gram),
                len(gram),
                frequency,
                self.ANALYSIS_VERSION,
            )
            for gram, frequency in ngram_frequencies.items()
            if self._is_content_gram(gram)
        )
