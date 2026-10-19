import os

from dash import Dash
from dynaconf import Dynaconf
from sqlalchemy import create_engine

from data import GenreRepository
from layout import build_layout

HOST = "127.0.0.1"
PORT = 8050
DEBUG = True

os.chdir(os.path.dirname(__file__))


def build_engine():
    settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
    return create_engine(settings.ENGINE_URL, echo=False)


if __name__ == "__main__":
    engine = build_engine()
    df = GenreRepository(engine).get_year_counts()

    app = Dash(title="Hot 100 Lyrics")
    app.layout = build_layout(df)

    app.run(host=HOST, port=PORT, debug=DEBUG)
