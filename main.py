import logging
import os

from dynaconf import Dynaconf
from sqlalchemy import create_engine
from etl import ETLProcessor

os.chdir(os.path.dirname(__file__))

BILLBOARD_PATH = "data/billboard-hot100-lyrics-main"
SPOTIFY_PATH = "data/spotify_tracks.csv"

def run():
    logging.basicConfig(level=logging.NOTSET)

    def build_engine():
        settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
        return create_engine(settings.ENGINE_URL, echo=False)

    engine = build_engine()


    with engine.connect() as conn:
        processor = ETLProcessor(
            conn,
            BILLBOARD_PATH,
            SPOTIFY_PATH
        )
        processor.process()

    engine.dispose()


if __name__ == "__main__":
    run()
