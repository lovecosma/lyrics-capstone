import logging
import os

from dynaconf import Dynaconf
from sqlalchemy import create_engine
from typesafe_sdk import AsyncTypeSafeClient

from services.etl import (
    TOPIC_TABLE,
    TRACK_ID_COLUMN,
    BillboardExtractor,
    EconomicIndicatorProcessor,
    EmotionLexiconProcessor,
    Extractor,
    FredExtractor,
    GenreMappingProcessor,
    Loader,
    NrcLexiconExtractor,
    ProfanityProcessor,
    TopicProcessor,
    TrackProcessor,
)
from services.genre_enrichment import (
    GenreEnricher,
    GenreEnrichmentProcessor,
    SnapshotGenreEnricher,
    TrackGenreEnricher,
)
from services.itunes import ITunesClient
from services.lyrics_analysis import (
    LyricsAnalysisProcessor,
    LyricsAnalyzer,
    LyricsTopicAnalyzer,
    LyricsTopicProcessor,
    SnapshotLyricsTopicAnalyzer,
)

os.chdir(os.path.dirname(__file__))

BILLBOARD_PATH = "data/billboard-hot100-lyrics-main"
SPOTIFY_PATH = "data/spotify_tracks.csv"
TOPIC_PATH = "data/topics.csv"
GENRE_SNAPSHOT_PATH = "data/itunes_track_genres.csv"
GENRE_MAPPING_PATH = "data/genre_mapping.csv"
LYRICS_TOPIC_SNAPSHOT_PATH = "data/typesafe_lyrics_topics.csv"
EMOTION_LEXICON_PATH = "data/NRC-Emotion-Lexicon-v0.92/emotion-lexicon.txt"
PROFANITY_PATH = "data/profanity_en.csv"
ECONOMIC_INDICATOR_PATH = "data/economic_indicators.csv"
FRED_PATH = "data/fred"
NON_CONTENT_WORD_PATHS = (
    "data/stopwords.txt",
    "data/lyric_stopwords.txt",
    "data/filler_words.txt",
)
LYRICS_ANALYSIS_BATCH_SIZE = 500
GENRE_SEARCH_BATCH_SIZE = 50
GENRE_SNAPSHOT_BATCH_SIZE = 500
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
        loader = Loader(conn)
        processors = (
            TrackProcessor(
                BillboardExtractor(conn), loader, BILLBOARD_PATH, SPOTIFY_PATH
            ),
            TopicProcessor(Extractor(conn), loader, TOPIC_PATH),
            EmotionLexiconProcessor(
                NrcLexiconExtractor(conn), loader, EMOTION_LEXICON_PATH
            ),
            ProfanityProcessor(Extractor(conn), loader, PROFANITY_PATH),
            EconomicIndicatorProcessor(
                FredExtractor(conn), loader, ECONOMIC_INDICATOR_PATH, FRED_PATH
            ),
        )
        for processor in processors:
            processor.process()

    engine.dispose()


def plan_track_batches(conn, processor, batch_size):
    with conn.begin():
        pending_track_ids = processor.select_pending()[TRACK_ID_COLUMN].tolist()
    track_id_batches = [
        pending_track_ids[batch_start : batch_start + batch_size]
        for batch_start in range(0, len(pending_track_ids), batch_size)
    ]
    logger.info(
        "Planned %d tracks in %d batches of up to %d",
        len(pending_track_ids),
        len(track_id_batches),
        batch_size,
    )
    return track_id_batches


def process_track_batch(conn, extractor, processor, track_ids):
    with conn.begin():
        track_batch_df = extractor.extract_tracks(track_ids)
    batch_result = processor.compute_batch(track_batch_df)
    with conn.begin():
        processor.load_batch(batch_result)


def run_in_batches(conn, extractor, processor, batch_size):
    track_id_batches = plan_track_batches(conn, processor, batch_size)
    for batch_number, track_ids in enumerate(track_id_batches, start=1):
        logger.info("Processing batch %d of %d", batch_number, len(track_id_batches))
        process_track_batch(conn, extractor, processor, track_ids)
        logger.info("Committed batch %d of %d", batch_number, len(track_id_batches))
    logger.info("Completed %d batches", len(track_id_batches))


def fill_missing_genres():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        processor = GenreEnrichmentProcessor(
            extractor, Loader(conn), TrackGenreEnricher(ITunesClient)
        )
        run_in_batches(conn, extractor, processor, GENRE_SEARCH_BATCH_SIZE)

    engine.dispose()


def load_genre_snapshot():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        snapshot_df = extractor.extract_from_csv(
            GENRE_SNAPSHOT_PATH, parse_dates=[GenreEnricher.GENRE_SEARCHED_AT_COLUMN]
        )
        processor = GenreEnrichmentProcessor(
            extractor, Loader(conn), SnapshotGenreEnricher(snapshot_df)
        )
        run_in_batches(conn, extractor, processor, GENRE_SNAPSHOT_BATCH_SIZE)

    engine.dispose()


def map_genres():
    engine = build_engine()

    with engine.begin() as conn:
        GenreMappingProcessor(
            Extractor(conn), Loader(conn), GENRE_MAPPING_PATH
        ).process()

    engine.dispose()


def analyze_lyrics():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        non_content_words = frozenset().union(
            *map(extractor.extract_word_list, NON_CONTENT_WORD_PATHS)
        )
        processor = LyricsAnalysisProcessor(
            extractor, Loader(conn), LyricsAnalyzer(non_content_words)
        )
        run_in_batches(conn, extractor, processor, LYRICS_ANALYSIS_BATCH_SIZE)

    engine.dispose()


def analyze_lyrics_topic():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        with conn.begin():
            topic_df = extractor.extract_from_db(TOPIC_TABLE)
        processor = LyricsTopicProcessor(
            extractor,
            Loader(conn),
            LyricsTopicAnalyzer(topic_df, build_typesafe_client),
        )
        run_in_batches(conn, extractor, processor, LYRICS_ANALYSIS_BATCH_SIZE)

    engine.dispose()


def load_lyrics_topic_snapshot():
    engine = build_engine()

    with engine.connect() as conn:
        extractor = Extractor(conn)
        with conn.begin():
            topic_df = extractor.extract_from_db(TOPIC_TABLE)
        snapshot_df = extractor.extract_from_csv(LYRICS_TOPIC_SNAPSHOT_PATH)
        processor = LyricsTopicProcessor(
            extractor,
            Loader(conn),
            SnapshotLyricsTopicAnalyzer(topic_df, snapshot_df),
        )
        run_in_batches(conn, extractor, processor, LYRICS_ANALYSIS_BATCH_SIZE)

    engine.dispose()


if __name__ == "__main__":
    configure_logging()
    run_etl()
    analyze_lyrics()
    load_lyrics_topic_snapshot()
    load_genre_snapshot()
    map_genres()
