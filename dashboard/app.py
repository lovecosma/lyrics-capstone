import os

import callbacks
from dash import Dash
from dynaconf import Dynaconf
from layout import build_layout, category_colors, main_topics
from sqlalchemy import create_engine

from data import (
    EconomyRepository,
    EmotionRepository,
    ExplicitRepository,
    GenreRepository,
    SoundRepository,
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
    explicit_repository = ExplicitRepository(engine)
    explicit_df = explicit_repository.get_year_rates()
    explicit_breakdown_df = explicit_repository.get_breakdown_counts()
    vocabulary_repository = VocabularyRepository(engine)
    emotion_repository = EmotionRepository(engine)
    emotion_df = emotion_repository.get_year_shares()
    genre_emotion_share_df = emotion_repository.get_genre_shares()
    sound_df = SoundRepository(engine).get_year_averages()
    economy_df = EconomyRepository(engine).get_year_averages()
    genre_distinctive_df = vocabulary_repository.get_genre_distinctive_terms()
    topic_distinctive_df = vocabulary_repository.get_topic_distinctive_terms(
        main_topics(topic_df)
    )
    shared_words = vocabulary_repository.get_shared_top_words()
    word_year_df = vocabulary_repository.get_word_year_counts()
    callbacks.set_data(
        genre_distinctive_df,
        topic_distinctive_df,
        category_colors(genre_df, "broad_genre"),
        category_colors(topic_df, "main_topic"),
        word_year_df,
    )

    app = Dash(title="Hot 100 Lyrics")
    app.layout = build_layout(
        genre_df,
        topic_df,
        topic_presence_df,
        genre_topic_share_df,
        genre_distinctive_df,
        topic_distinctive_df,
        shared_words,
        word_year_df,
        explicit_df,
        explicit_breakdown_df,
        emotion_df,
        genre_emotion_share_df,
        sound_df,
        economy_df,
    )

    app.run(host=HOST, port=PORT, debug=DEBUG)
