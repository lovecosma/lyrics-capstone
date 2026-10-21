import logging

import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

from services.etl import (
    BillboardExtractor,
    EmotionLexiconProcessor,
    Extractor,
    Loader,
    NrcLexiconExtractor,
    TopicProcessor,
    TrackProcessor,
)

logger = logging.getLogger(__name__)

SQL_DIR = "/opt/airflow/sql"
SCHEMA_PATH = "lyrics-schema.sql"
VIEWS_PATH = "lyrics-views.sql"
CONN_ID = "billboard-postgres"
DATA_DIR = "/opt/airflow/data"
BILLBOARD_PATH = f"{DATA_DIR}/billboard-hot100-lyrics-main"
SPOTIFY_PATH = f"{DATA_DIR}/spotify_tracks.csv"
TOPIC_PATH = f"{DATA_DIR}/topics.csv"
NRC_LEXICON_DIR = f"{DATA_DIR}/NRC-Emotion-Lexicon-v0.92"
EMOTION_LEXICON_PATH = f"{NRC_LEXICON_DIR}/emotion-lexicon.txt"


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

    schema_sql >> views_sql >> load_tracks() >> load_topics() >> load_emotion_lexicon()


etl_dag()
