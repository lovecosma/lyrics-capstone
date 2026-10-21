import logging

import pendulum
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task

logger = logging.getLogger(__name__)

SQL_DIR = "/opt/airflow/sql"
SCHEMA_PATH = "lyrics-schema.sql"
VIEWS_PATH = "lyrics-views.sql"
CONN_ID = "billboard-postgres"

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
    def run_etl():
        logger.info("Connecting to billboard-postgres")
        hook = PostgresHook(postgres_conn_id=CONN_ID)
        # engine = hook.get_sqlalchemy_engine()
        # etl_processor = ETLProcessor(engine, CSV_PATH)
        # etl_processor.process()
        # engine.dispose()
        # logger.info("Disposed songs-postgres engine")


etl_dag()
