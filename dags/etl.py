import logging
from functools import partial

import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Variable, dag, task, task_group
from typesafe_sdk import AsyncTypeSafeClient

from services.batching import run_in_batches
from services.etl import (
    TOPIC_TABLE,
    BillboardExtractor,
    EconomicIndicatorProcessor,
    EmotionLexiconProcessor,
    Extractor,
    FredExtractor,
    Loader,
    NrcLexiconExtractor,
    ProfanityProcessor,
    TopicProcessor,
    TrackProcessor,
)
from services.lyrics_analysis import (
    LyricsAnalysisProcessor,
    LyricsAnalyzer,
    LyricsTopicAnalyzer,
    LyricsTopicProcessor,
    LyricsTopicSnapshotProcessor,
    SnapshotLyricsTopicAnalyzer,
)

logger = logging.getLogger(__name__)

SQL_DIR = "/opt/airflow/sql"
SCHEMA_PATH = "lyrics-schema.sql"
VIEWS_PATH = "lyrics-views.sql"
CONN_ID = "billboard_postgres"
DATA_DIR = "/opt/airflow/data"
BILLBOARD_PATH = f"{DATA_DIR}/billboard-hot100-lyrics-main"
SPOTIFY_PATH = f"{DATA_DIR}/spotify_tracks.csv"
TOPIC_PATH = f"{DATA_DIR}/topics.csv"
NRC_LEXICON_DIR = f"{DATA_DIR}/NRC-Emotion-Lexicon-v0.92"
EMOTION_LEXICON_PATH = f"{NRC_LEXICON_DIR}/emotion-lexicon.txt"
PROFANITY_PATH = f"{DATA_DIR}/profanity_en.csv"
ECONOMIC_INDICATOR_PATH = f"{DATA_DIR}/economic_indicators.csv"
FRED_PATH = f"{DATA_DIR}/fred"
NON_CONTENT_WORD_PATHS = (
    f"{DATA_DIR}/stopwords.txt",
    f"{DATA_DIR}/lyric_stopwords.txt",
    f"{DATA_DIR}/filler_words.txt",
)
LYRICS_ANALYSIS_BATCH_SIZE = 500
LYRICS_TOPIC_SNAPSHOT_PATH = f"{DATA_DIR}/typesafe_lyrics_topics.csv"
TYPESAFE_API_KEY_VARIABLE = "typesafe_ai_api_key"


@dag(
    schedule=None,
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    template_searchpath=[SQL_DIR],
    tags=["billboard"],
)
def etl_dag():
    schema_sql = SQLExecuteQueryOperator(
        task_id="billboard_schema",
        sql=SCHEMA_PATH,
        conn_id=CONN_ID,
    )

    views_sql = SQLExecuteQueryOperator(
        task_id="billboard_views",
        sql=VIEWS_PATH,
        conn_id=CONN_ID,
    )

    @task_group()
    def etl():
        @task()
        def load_tracks():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                TrackProcessor(
                    BillboardExtractor(conn), Loader(conn), BILLBOARD_PATH, SPOTIFY_PATH
                ).process()
            engine.dispose()

        @task()
        def load_topics():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                TopicProcessor(Extractor(conn), Loader(conn), TOPIC_PATH).process()
            engine.dispose()

        @task()
        def load_emotion_lexicon():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                EmotionLexiconProcessor(
                    NrcLexiconExtractor(conn), Loader(conn), EMOTION_LEXICON_PATH
                ).process()
            engine.dispose()

        @task()
        def load_profanity():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                ProfanityProcessor(
                    Extractor(conn), Loader(conn), PROFANITY_PATH
                ).process()
            engine.dispose()

        @task()
        def load_economic_indicators():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                EconomicIndicatorProcessor(
                    FredExtractor(conn),
                    Loader(conn),
                    ECONOMIC_INDICATOR_PATH,
                    FRED_PATH,
                ).process()
            engine.dispose()

        (
            load_tracks()
            >> load_topics()
            >> load_emotion_lexicon()
            >> load_profanity()
            >> load_economic_indicators()
        )

    @task_group()
    def lyrics_analysis():
        @task()
        def analyze_lyrics_metrics():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
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

        @task()
        def load_lyrics_topic_snapshot():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.connect() as conn:
                extractor = Extractor(conn)
                with conn.begin():
                    topic_df = extractor.extract_from_db(TOPIC_TABLE)
                snapshot_df = extractor.extract_snapshot(
                    LYRICS_TOPIC_SNAPSHOT_PATH,
                    SnapshotLyricsTopicAnalyzer.SNAPSHOT_COLUMNS,
                )
                processor = LyricsTopicProcessor(
                    extractor,
                    Loader(conn),
                    SnapshotLyricsTopicAnalyzer(topic_df, snapshot_df),
                )
                run_in_batches(conn, extractor, processor, LYRICS_ANALYSIS_BATCH_SIZE)
            engine.dispose()

        @task()
        def analyze_lyrics_topic():
            create_client = partial(
                AsyncTypeSafeClient, api_key=Variable.get(TYPESAFE_API_KEY_VARIABLE)
            )
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.connect() as conn:
                extractor = Extractor(conn)
                with conn.begin():
                    topic_df = extractor.extract_from_db(TOPIC_TABLE)
                processor = LyricsTopicProcessor(
                    extractor,
                    Loader(conn),
                    LyricsTopicAnalyzer(topic_df, create_client),
                )
                run_in_batches(conn, extractor, processor, LYRICS_ANALYSIS_BATCH_SIZE)
            engine.dispose()

        @task()
        def export_lyrics_topic_snapshot():
            engine = PostgresHook(postgres_conn_id=CONN_ID).get_sqlalchemy_engine()
            with engine.begin() as conn:
                LyricsTopicSnapshotProcessor(
                    Extractor(conn), Loader(conn), LYRICS_TOPIC_SNAPSHOT_PATH
                ).process()
            engine.dispose()

        (
            analyze_lyrics_metrics()
            >> load_lyrics_topic_snapshot()
            >> analyze_lyrics_topic()
            >> export_lyrics_topic_snapshot()
        )

    (schema_sql >> views_sql >> etl() >> lyrics_analysis())


etl_dag()
