import asyncio
import logging
import re

import pandas as pd
from lexicalrichness import LexicalRichness
from nltk import FreqDist
from nltk.tokenize import RegexpTokenizer
from nltk.util import everygrams
from typesafe_sdk import Choice, Noul, TypeSafeError

from services.etl import (
    LYRICS_METRIC_TABLE,
    LYRICS_NGRAM_METRIC_TABLE,
    LYRICS_TOPIC_TABLE,
    TOPIC_TABLE,
    TRACK_TABLE,
)

logger = logging.getLogger(__name__)


class LyricsCleaner:
    SCRAPE_ARTIFACT_PATTERN = re.compile(
        # 3 ContributorsHello Lyrics
        r"^\s*\d+ Contributors?.*?Lyrics"
        # See Adele LiveGet tickets as low as $45
        r"|See .+? LiveGet tickets as low as \$\d+"
        r"|You might also like"
        # 42Embed
        r"|Embed\s*$"
    )
    SCRAPE_ARTIFACT_REPLACEMENT = "\n"
    OPTIONAL_SPACE = r"[ \t]*"
    REQUIRED_SPACE = r"[ \t]+"
    SECTION_NAME = r"(?:verse|chorus|hook|bridge|intro|outro|pre-chorus|refrain)"
    # " 2"
    SECTION_NUMBER = rf"(?:{OPTIONAL_SPACE}\d+)?"
    # " 16X", " - 112 (Q", ": Drake"
    BRACKETED_NOTE = rf"(?:{OPTIONAL_SPACE}(?:\d|x\d|[-:])[^\])}}\n]*)?"
    # " x2", " 4x", " until end", " repeat"
    REPEAT_NOTE = rf"(?:{REQUIRED_SPACE}(?:\d+x|x\d+|until end|repeat))?"
    # {Chorus}, (Chorus 16X), [Hook - 112 (Q)
    BRACKETED_SECTION_HEADER = (
        rf"[\[({{]{OPTIONAL_SPACE}{SECTION_NAME}{BRACKETED_NOTE}[\])}}]?"
    )
    # -CHORUS-, -- Verse 2 --
    DASHED_SECTION_HEADER = (
        rf"-+{OPTIONAL_SPACE}{SECTION_NAME}{SECTION_NUMBER}{OPTIONAL_SPACE}-+"
    )
    # Verse 1:, Chorus x2, Chorus until end
    BARE_SECTION_HEADER = (
        rf"{SECTION_NAME}{SECTION_NUMBER}{OPTIONAL_SPACE}:?{REPEAT_NOTE}"
    )
    SECTION_HEADER_PATTERN = re.compile(
        rf"^{OPTIONAL_SPACE}"
        rf"(?:{BRACKETED_SECTION_HEADER}|{DASHED_SECTION_HEADER}|{BARE_SECTION_HEADER})"
        rf"{OPTIONAL_SPACE}$",
        re.IGNORECASE | re.MULTILINE,
    )
    SECTION_HEADER_REPLACEMENT = ""

    def clean(self, lyrics):
        without_artifacts = self.SCRAPE_ARTIFACT_PATTERN.sub(
            self.SCRAPE_ARTIFACT_REPLACEMENT, lyrics
        )
        return self.SECTION_HEADER_PATTERN.sub(
            self.SECTION_HEADER_REPLACEMENT, without_artifacts
        )


class LyricsTokenizer:
    CHARACTER_NORMALIZATION = str.maketrans(
        {"\u2019": "'", "\u2018": "'", "\u200b": None}
    )
    # "don't stop, rock'n'roll_2am lovin' café!"
    # -> don't, stop, rock'n'roll, 2am, lovin, café
    WORD_TOKENIZER = RegexpTokenizer(r"[^\W_]+(?:'[^\W_]+)*")

    def tokenize(self, lyrics):
        normalized = lyrics.translate(self.CHARACTER_NORMALIZATION).casefold()
        lines = (self.WORD_TOKENIZER.tokenize(line) for line in normalized.splitlines())
        return [line for line in lines if line]


class LyricsAnalyzer:
    ANALYSIS_VERSION = "v3"
    MIN_NGRAM_SIZE = 1
    MAX_NGRAM_SIZE = 3
    NGRAM_SEPARATOR = " "
    TRACK_ID_COLUMN = "track_id"
    LYRICS_COLUMN = "lyrics"
    WORD_COUNT_COLUMN = "word_count"
    UNIQUE_WORD_COUNT_COLUMN = "unique_word_count"
    LEXICAL_DIVERSITY_COLUMN = "lexical_diversity"
    AVERAGE_WORD_LENGTH_COLUMN = "average_word_length"
    NGRAM_COLUMN = "ngram"
    NGRAM_SIZE_COLUMN = "n"
    FREQUENCY_COLUMN = "frequency"
    ANALYSIS_VERSION_COLUMN = "analysis_version"
    LYRICS_METRIC_COLUMNS = (
        TRACK_ID_COLUMN,
        WORD_COUNT_COLUMN,
        UNIQUE_WORD_COUNT_COLUMN,
        LEXICAL_DIVERSITY_COLUMN,
        AVERAGE_WORD_LENGTH_COLUMN,
        ANALYSIS_VERSION_COLUMN,
    )
    LYRICS_NGRAM_METRIC_COLUMNS = (
        TRACK_ID_COLUMN,
        NGRAM_COLUMN,
        NGRAM_SIZE_COLUMN,
        FREQUENCY_COLUMN,
        ANALYSIS_VERSION_COLUMN,
    )

    def __init__(self, non_content_words):
        self._cleaner = LyricsCleaner()
        self._tokenizer = LyricsTokenizer()
        self._non_content_words = frozenset(non_content_words)

    def select_unanalyzed(self, track_df, lyrics_metric_df):
        is_current_version = lyrics_metric_df[self.ANALYSIS_VERSION_COLUMN].eq(
            self.ANALYSIS_VERSION
        )
        analyzed_track_ids = lyrics_metric_df[self.TRACK_ID_COLUMN][is_current_version]
        return track_df[~track_df[self.TRACK_ID_COLUMN].isin(analyzed_track_ids)]

    def analyze(self, track_df):
        logger.info("Analyzing lyrics for %d tracks", len(track_df))
        lyrics_metrics, lyrics_ngram_metrics = self._compute_track_metrics(track_df)
        lyrics_metric_df = pd.DataFrame(
            lyrics_metrics, columns=list(self.LYRICS_METRIC_COLUMNS)
        )
        lyrics_ngram_metric_df = pd.DataFrame(
            lyrics_ngram_metrics, columns=list(self.LYRICS_NGRAM_METRIC_COLUMNS)
        )
        self._warn_about_wordless_tracks(lyrics_metric_df)
        logger.info(
            "Computed %d lyrics metrics and %d n-gram metrics",
            len(lyrics_metric_df),
            len(lyrics_ngram_metric_df),
        )
        return lyrics_metric_df, lyrics_ngram_metric_df

    def _compute_track_metrics(self, track_df):
        lyrics_metrics = []
        lyrics_ngram_metrics = []
        for track_id, lyrics in zip(
            track_df[self.TRACK_ID_COLUMN], track_df[self.LYRICS_COLUMN]
        ):
            lines = self._tokenize_lyrics(lyrics)
            lyrics_metrics.append(self._compute_lyrics_metric(track_id, lines))
            lyrics_ngram_metrics.extend(
                self._compute_lyrics_ngram_metrics(track_id, lines)
            )
        return lyrics_metrics, lyrics_ngram_metrics

    def _tokenize_lyrics(self, lyrics):
        return self._tokenizer.tokenize(self._cleaner.clean(lyrics))

    def _warn_about_wordless_tracks(self, lyrics_metric_df):
        wordless_track_count = lyrics_metric_df[self.WORD_COUNT_COLUMN].eq(0).sum()
        if wordless_track_count:
            logger.warning(
                "%d tracks have no words after cleaning lyrics", wordless_track_count
            )

    def _compute_lyrics_metric(self, track_id, lines):
        words = [word for line in lines for word in line]
        return {
            self.TRACK_ID_COLUMN: track_id,
            self.WORD_COUNT_COLUMN: len(words),
            self.UNIQUE_WORD_COUNT_COLUMN: len(set(words)),
            self.LEXICAL_DIVERSITY_COLUMN: self._compute_lexical_diversity(words),
            self.AVERAGE_WORD_LENGTH_COLUMN: self._compute_average_word_length(words),
            self.ANALYSIS_VERSION_COLUMN: self.ANALYSIS_VERSION,
        }

    def _compute_lexical_diversity(self, words):
        if not words:
            return None
        return LexicalRichness(words, preprocessor=None, tokenizer=None).mtld()

    def _compute_average_word_length(self, words):
        if not words:
            return None
        return sum(map(len, words)) / len(words)

    def _compute_lyrics_ngram_metrics(self, track_id, lines):
        ngram_frequencies = FreqDist(
            gram
            for line in lines
            for gram in everygrams(line, self.MIN_NGRAM_SIZE, self.MAX_NGRAM_SIZE)
        )
        return (
            {
                self.TRACK_ID_COLUMN: track_id,
                self.NGRAM_COLUMN: self.NGRAM_SEPARATOR.join(gram),
                self.NGRAM_SIZE_COLUMN: len(gram),
                self.FREQUENCY_COLUMN: frequency,
                self.ANALYSIS_VERSION_COLUMN: self.ANALYSIS_VERSION,
            }
            for gram, frequency in ngram_frequencies.items()
            if self._is_content_gram(gram)
        )

    def _is_content_gram(self, gram):
        return not all(word in self._non_content_words for word in gram)


class TopicAnalyzer:
    ANALYSIS_VERSION = "v1"
    TRACK_ID_COLUMN = "track_id"
    TOPIC_ID_COLUMN = "topic_id"
    TOPIC_NAME_COLUMN = "name"
    IS_PRIMARY_COLUMN = "is_primary"
    PRIMARY_PROBABILITY_COLUMN = "primary_probability"
    PRESENCE_PROBABILITY_COLUMN = "presence_probability"
    MODEL_VERSION_COLUMN = "model_version"
    ANALYSIS_VERSION_COLUMN = "analysis_version"
    LYRICS_TOPIC_COLUMNS = (
        TRACK_ID_COLUMN,
        TOPIC_ID_COLUMN,
        IS_PRIMARY_COLUMN,
        PRIMARY_PROBABILITY_COLUMN,
        PRESENCE_PROBABILITY_COLUMN,
        MODEL_VERSION_COLUMN,
        ANALYSIS_VERSION_COLUMN,
    )

    def __init__(self, topic_df):
        self._topic_ids = dict(
            zip(topic_df[self.TOPIC_NAME_COLUMN], topic_df[self.TOPIC_ID_COLUMN])
        )

    def select_uncategorized(self, track_df, lyrics_topic_df):
        is_current_version = lyrics_topic_df[self.ANALYSIS_VERSION_COLUMN].eq(
            self.ANALYSIS_VERSION
        )
        categorized_track_ids = lyrics_topic_df[self.TRACK_ID_COLUMN][
            is_current_version
        ]
        return track_df[~track_df[self.TRACK_ID_COLUMN].isin(categorized_track_ids)]


class LyricsTopicAnalyzer(TopicAnalyzer):
    MAX_CONCURRENT_REQUESTS = 8
    OTHER_TOPIC = "other"
    PRIMARY_TOPIC_QUESTION_ID = "primary_topic"
    PRIMARY_TOPIC_INSTRUCTIONS = (
        "What is the main theme of the lyrics in `song.lyrics`?"
    )
    TOPIC_PRESENCE_QUESTION = (
        "Is `theme` a substantial theme of the lyrics in `song.lyrics`, "
        "beyond a single passing line?"
    )
    TOPIC_DESCRIPTION_COLUMN = "description"

    def __init__(self, topic_df, create_client):
        super().__init__(topic_df)
        self._create_client = create_client
        self._cleaner = LyricsCleaner()
        self._questions = self._build_questions(
            dict(
                zip(
                    topic_df[self.TOPIC_NAME_COLUMN],
                    topic_df[self.TOPIC_DESCRIPTION_COLUMN],
                )
            )
        )

    def analyze(self, track_df):
        logger.info("Categorizing lyrics for %d tracks", len(track_df))
        track_topic_rows = asyncio.run(self._classify_tracks(track_df))
        lyrics_topic_df = pd.DataFrame(
            [row for rows in track_topic_rows for row in rows],
            columns=list(self.LYRICS_TOPIC_COLUMNS),
        )
        classified_track_count = lyrics_topic_df[self.TRACK_ID_COLUMN].nunique()
        logger.info(
            "Categorized %d of %d tracks", classified_track_count, len(track_df)
        )
        return lyrics_topic_df

    def _build_questions(self, topic_descriptions):
        primary_topic_question = Choice(
            instructions=self.PRIMARY_TOPIC_INSTRUCTIONS, criteria=topic_descriptions
        )
        topic_presence_questions = {
            topic: self._build_presence_question(description)
            for topic, description in topic_descriptions.items()
            if topic != self.OTHER_TOPIC
        }
        return {
            self.PRIMARY_TOPIC_QUESTION_ID: primary_topic_question,
            **topic_presence_questions,
        }

    def _build_presence_question(self, topic_description):
        return Noul(
            instructions={
                "question": self.TOPIC_PRESENCE_QUESTION,
                "theme": topic_description,
            }
        )

    async def _classify_tracks(self, track_df):
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        async with self._create_client() as client:
            return await asyncio.gather(
                *(
                    self._classify_track(client, semaphore, track)
                    for track in track_df.itertuples(index=False)
                )
            )

    async def _classify_track(self, client, semaphore, track):
        async with semaphore:
            try:
                response = await client.system_one(
                    self._build_song_state(track), self._questions
                )
                return self._build_lyrics_topic_rows(track, response)
            except (TypeSafeError, KeyError) as error:
                logger.warning(
                    "Topic classification failed for %s - %s (%s: %s)",
                    track.title,
                    track.artist_name,
                    type(error).__name__,
                    error,
                )
                return []

    def _build_song_state(self, track):
        return {
            "song": {
                "title": track.title,
                "artist": track.artist_name,
                "lyrics": self._cleaner.clean(track.lyrics),
            }
        }

    def _build_lyrics_topic_rows(self, track, response):
        primary_topic = response.choices[self.PRIMARY_TOPIC_QUESTION_ID]
        return [
            {
                self.TRACK_ID_COLUMN: track.track_id,
                self.TOPIC_ID_COLUMN: topic_id,
                self.IS_PRIMARY_COLUMN: topic == primary_topic.choice,
                self.PRIMARY_PROBABILITY_COLUMN: primary_topic.probabilities[topic],
                self.PRESENCE_PROBABILITY_COLUMN: self._get_presence_probability(
                    response, topic
                ),
                self.MODEL_VERSION_COLUMN: response.model,
                self.ANALYSIS_VERSION_COLUMN: self.ANALYSIS_VERSION,
            }
            for topic, topic_id in self._topic_ids.items()
        ]

    def _get_presence_probability(self, response, topic):
        if topic == self.OTHER_TOPIC:
            return None
        return response.nouls[topic].noul


class SnapshotLyricsTopicAnalyzer(TopicAnalyzer):
    TITLE_COLUMN = "title"
    ARTIST_NAME_COLUMN = "artist_name"
    TOPIC_COLUMN = "topic"
    PROBABILITY_COLUMNS = (
        TopicAnalyzer.PRIMARY_PROBABILITY_COLUMN,
        TopicAnalyzer.PRESENCE_PROBABILITY_COLUMN,
    )
    SNAPSHOT_COLUMNS = (
        TITLE_COLUMN,
        ARTIST_NAME_COLUMN,
        TOPIC_COLUMN,
        TopicAnalyzer.IS_PRIMARY_COLUMN,
        *PROBABILITY_COLUMNS,
        TopicAnalyzer.MODEL_VERSION_COLUMN,
        TopicAnalyzer.ANALYSIS_VERSION_COLUMN,
    )

    def __init__(self, topic_df, snapshot_df):
        super().__init__(topic_df)
        self._snapshot_df = snapshot_df

    def analyze(self, track_df):
        is_current_version = self._snapshot_df[self.ANALYSIS_VERSION_COLUMN].eq(
            self.ANALYSIS_VERSION
        )
        snapshot_topic_df = track_df[
            [self.TRACK_ID_COLUMN, self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN]
        ].merge(
            self._snapshot_df[is_current_version],
            on=[self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN],
        )
        lyrics_topic_df = (
            snapshot_topic_df.assign(
                **{
                    self.TOPIC_ID_COLUMN: snapshot_topic_df[self.TOPIC_COLUMN].map(
                        self._topic_ids
                    )
                }
            )
            .dropna(subset=[self.TOPIC_ID_COLUMN])
            .astype({self.TOPIC_ID_COLUMN: int})[list(self.LYRICS_TOPIC_COLUMNS)]
        )
        logger.info(
            "Restored topics for %d of %d tracks from the snapshot",
            lyrics_topic_df[self.TRACK_ID_COLUMN].nunique(),
            len(track_df),
        )
        return lyrics_topic_df


class LyricsAnalysisProcessor:
    def __init__(self, extractor, loader, analyzer):
        self._extractor = extractor
        self._loader = loader
        self._analyzer = analyzer

    def select_pending(self):
        track_df = self._extractor.extract_from_db(TRACK_TABLE)
        unanalyzed_track_df = self._analyzer.select_unanalyzed(
            track_df, self._extractor.extract_from_db(LYRICS_METRIC_TABLE)
        )
        logger.info(
            "%d of %d tracks need lyrics analysis",
            len(unanalyzed_track_df),
            len(track_df),
        )
        return unanalyzed_track_df

    def compute_batch(self, track_batch_df):
        return self._analyzer.analyze(track_batch_df)

    def load_batch(self, batch_result):
        lyrics_metric_df, lyrics_ngram_metric_df = batch_result
        self._loader.copy_to_db(lyrics_metric_df, LYRICS_METRIC_TABLE)
        self._loader.copy_to_db(lyrics_ngram_metric_df, LYRICS_NGRAM_METRIC_TABLE)


class LyricsTopicProcessor:
    def __init__(self, extractor, loader, analyzer):
        self._extractor = extractor
        self._loader = loader
        self._analyzer = analyzer

    def select_pending(self):
        track_df = self._extractor.extract_from_db(TRACK_TABLE)
        uncategorized_track_df = self._analyzer.select_uncategorized(
            track_df, self._extractor.extract_from_db(LYRICS_TOPIC_TABLE)
        )
        logger.info(
            "%d of %d tracks need lyrics categorization",
            len(uncategorized_track_df),
            len(track_df),
        )
        return uncategorized_track_df

    def compute_batch(self, track_batch_df):
        return self._analyzer.analyze(track_batch_df)

    def load_batch(self, batch_result):
        self._loader.copy_to_db(batch_result, LYRICS_TOPIC_TABLE)


class LyricsTopicSnapshotProcessor:
    TRACK_ID_COLUMN = TopicAnalyzer.TRACK_ID_COLUMN
    TOPIC_ID_COLUMN = TopicAnalyzer.TOPIC_ID_COLUMN
    TOPIC_NAME_COLUMN = TopicAnalyzer.TOPIC_NAME_COLUMN
    TITLE_COLUMN = SnapshotLyricsTopicAnalyzer.TITLE_COLUMN
    ARTIST_NAME_COLUMN = SnapshotLyricsTopicAnalyzer.ARTIST_NAME_COLUMN
    TOPIC_COLUMN = SnapshotLyricsTopicAnalyzer.TOPIC_COLUMN
    ANALYSIS_VERSION_COLUMN = TopicAnalyzer.ANALYSIS_VERSION_COLUMN
    PROBABILITY_COLUMNS = SnapshotLyricsTopicAnalyzer.PROBABILITY_COLUMNS
    SNAPSHOT_COLUMNS = SnapshotLyricsTopicAnalyzer.SNAPSHOT_COLUMNS
    SNAPSHOT_KEY_COLUMNS = (
        TITLE_COLUMN,
        ARTIST_NAME_COLUMN,
        TOPIC_COLUMN,
        ANALYSIS_VERSION_COLUMN,
    )

    def __init__(self, extractor, loader, snapshot_csv_path):
        self._extractor = extractor
        self._loader = loader
        self._snapshot_csv_path = snapshot_csv_path

    def process(self):
        logger.info("Starting lyrics topic snapshot export")
        snapshot_df = self._extractor.extract_snapshot(
            self._snapshot_csv_path, self.SNAPSHOT_COLUMNS
        )
        db_snapshot_df = self._build_snapshot_rows(
            self._extractor.extract_from_db(LYRICS_TOPIC_TABLE),
            self._extractor.extract_from_db(TRACK_TABLE),
            self._extractor.extract_from_db(TOPIC_TABLE),
        )
        merged_snapshot_df = pd.concat(
            [snapshot_df, db_snapshot_df], ignore_index=True
        ).drop_duplicates(subset=list(self.SNAPSHOT_KEY_COLUMNS))
        logger.info(
            "Added %d rows to the lyrics topic snapshot",
            len(merged_snapshot_df) - len(snapshot_df),
        )
        self._loader.save_to_csv(merged_snapshot_df, self._snapshot_csv_path)
        logger.info("Completed lyrics topic snapshot export")

    def _build_snapshot_rows(self, lyrics_topic_df, track_df, topic_df):
        return (
            lyrics_topic_df.merge(
                track_df[
                    [self.TRACK_ID_COLUMN, self.TITLE_COLUMN, self.ARTIST_NAME_COLUMN]
                ],
                on=self.TRACK_ID_COLUMN,
            )
            .merge(
                topic_df[[self.TOPIC_ID_COLUMN, self.TOPIC_NAME_COLUMN]],
                on=self.TOPIC_ID_COLUMN,
            )
            .rename(columns={self.TOPIC_NAME_COLUMN: self.TOPIC_COLUMN})
            .astype(dict.fromkeys(self.PROBABILITY_COLUMNS, float))[
                list(self.SNAPSHOT_COLUMNS)
            ]
        )
