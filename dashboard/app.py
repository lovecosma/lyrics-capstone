import os

import callbacks
from dash import Dash
from dynaconf import Dynaconf
from layout import build_layout, category_colors
from sqlalchemy import create_engine

from data import (
    EmotionRepository,
    GenreRepository,
    TopicRepository,
    VocabularyRepository,
)

HOST = "127.0.0.1"
PORT = 8050
DEBUG = True

os.chdir(os.path.dirname(__file__))


def build_engine():
    settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
    return create_engine(settings.ENGINE_URL, echo=False)


if __name__ == "__main__":
    engine = build_engine()
    genre_repository = GenreRepository(engine)
    genre_df = genre_repository.get_year_counts()
    genre_topic_share_df = genre_repository.get_topic_shares()
    topic_repository = TopicRepository(engine)
    topic_df = topic_repository.get_year_counts()
    topic_presence_df = topic_repository.get_presence_year_counts()
    vocabulary_repository = VocabularyRepository(engine)
    explicit_df = vocabulary_repository.get_explicit_year_rates()
    emotion_df = EmotionRepository(engine).get_year_shares()
    distinctive_df = vocabulary_repository.get_distinctive_terms()
    shared_words = vocabulary_repository.get_shared_top_words()
    callbacks.set_data(distinctive_df, category_colors(genre_df, "broad_genre"))

    app = Dash(title="Hot 100 Lyrics")
    app.layout = build_layout(
        genre_df,
        topic_df,
        topic_presence_df,
        genre_topic_share_df,
        distinctive_df,
        shared_words,
        explicit_df,
        emotion_df,
    )

    app.run(host=HOST, port=PORT, debug=DEBUG)
