import logging
import os

from dynaconf import Dynaconf
from sqlalchemy import create_engine
from typesafe_sdk import AsyncTypeSafeClient

from etl import ETLProcessor, Extractor, Loader
from lyrics_analysis import LyricsAnalyzer, LyricsTopicAnalyzer

os.chdir(os.path.dirname(__file__))

BILLBOARD_PATH = "data/billboard-hot100-lyrics-main"
SPOTIFY_PATH = "data/spotify_tracks.csv"
TOPIC_PATH = "data/topics.csv"
NON_CONTENT_WORD_PATHS = (
    "data/stopwords.txt",
    "data/lyric_stopwords.txt",
    "data/filler_words.txt",
)
LYRICS_ANALYSIS_BATCH_SIZE = 500
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def build_engine():
    settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
    return create_engine(settings.ENGINE_URL, echo=False)


def build_typesafe_client():
    settings = Dynaconf(envvar_prefix="TYPESAFE_AI", load_dotenv=True)
    return AsyncTypeSafeClient(api_key=settings.API_KEY)


def run_etl():
    engine = build_engine()

    with engine.begin() as conn:
        processor = ETLProcessor(conn, BILLBOARD_PATH, SPOTIFY_PATH, TOPIC_PATH)
        processor.process()

    engine.dispose()


def analyze_lyrics():
    engine = build_engine()

    with engine.begin() as conn:
        extractor = Extractor(conn)
        loader = Loader(conn)
        non_content_words = frozenset().union(
            *map(extractor.extract_word_list, NON_CONTENT_WORD_PATHS)
        )
        analyzer = LyricsAnalyzer(non_content_words)
        track_df = extractor.extract_from_db("track")
        batch_starts = range(0, len(track_df), LYRICS_ANALYSIS_BATCH_SIZE)
        logger.info(
            "Starting lyrics analysis of %d tracks in %d batches of up to %d",
            len(track_df),
            len(batch_starts),
            LYRICS_ANALYSIS_BATCH_SIZE,
        )

        for batch_number, batch_start in enumerate(batch_starts, start=1):
            track_batch_df = track_df.iloc[
                batch_start : batch_start + LYRICS_ANALYSIS_BATCH_SIZE
            ]
            logger.info(
                "Processing lyrics batch %d of %d", batch_number, len(batch_starts)
            )
            lyrics_metric_df, lyrics_ngram_metric_df = analyzer.analyze(track_batch_df)
            loader.copy_to_db(lyrics_metric_df, "lyrics_metric")
            loader.copy_to_db(lyrics_ngram_metric_df, "lyrics_ngram_metric")

        logger.info("Completed lyrics analysis of %d tracks", len(track_df))

    engine.dispose()


def analyze_lyrics_topic():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        loader = Loader(conn)
        with conn.begin():
            track_df = extractor.extract_from_db("track")
            topic_df = extractor.extract_from_db("topic")
            lyrics_topic_df = extractor.extract_from_db("lyrics_topic")

        analyzer = LyricsTopicAnalyzer(topic_df, build_typesafe_client)
        uncategorized_track_df = analyzer.select_uncategorized(
            track_df, lyrics_topic_df
        )
        batch_starts = range(
            0, len(uncategorized_track_df), LYRICS_ANALYSIS_BATCH_SIZE
        )
        logger.info(
            "Starting lyrics categorization of %d of %d tracks in %d batches of up to %d",
            len(uncategorized_track_df),
            len(track_df),
            len(batch_starts),
            LYRICS_ANALYSIS_BATCH_SIZE,
        )

        for batch_number, batch_start in enumerate(batch_starts, start=1):
            track_batch_df = uncategorized_track_df.iloc[
                batch_start : batch_start + LYRICS_ANALYSIS_BATCH_SIZE
            ]
            logger.info(
                "Processing categorization batch %d of %d",
                batch_number,
                len(batch_starts),
            )
            lyrics_topic_batch_df = analyzer.analyze(track_batch_df)
            with conn.begin():
                loader.copy_to_db(lyrics_topic_batch_df, "lyrics_topic")

        logger.info(
            "Completed lyrics categorization of %d tracks", len(uncategorized_track_df)
        )

    engine.dispose()


if __name__ == "__main__":
    configure_logging()
    # run_etl()
    # analyze_lyrics()
    analyze_lyrics_topic()
