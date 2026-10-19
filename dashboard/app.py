import os

from dash import Dash
from dynaconf import Dynaconf
from sqlalchemy import create_engine

from data import GenreRepository, TopicRepository
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
    genre_df = GenreRepository(engine).get_year_counts()
    topic_repository = TopicRepository(engine)
    topic_df = topic_repository.get_year_counts()
    topic_presence_df = topic_repository.get_presence_year_counts()

    app = Dash(title="Hot 100 Lyrics")
    app.layout = build_layout(genre_df, topic_df, topic_presence_df)

    app.run(host=HOST, port=PORT, debug=DEBUG)
