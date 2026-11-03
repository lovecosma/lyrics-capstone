"""Exports the dashboard's data to Parquet files, so the app can run without a database.

The DAG's export_dashboard_snapshot task runs this after every pipeline run.
To export by hand: python dashboard/snapshot.py
"""

from pathlib import Path

import pandas as pd
from dynaconf import Dynaconf
from sqlalchemy import create_engine

from data import (
    EconomyRepository,
    EmotionRepository,
    ExplicitRepository,
    GenreRepository,
    SoundRepository,
    TopicRepository,
    VocabularyRepository,
    main_topics,
)

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"
SNAPSHOT_SUFFIX = ".parquet"
SHARED_WORDS = "shared_words"
SHARED_WORD_COLUMN = "word"


def build_engine():
    settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
    return create_engine(settings.ENGINE_URL, echo=False)


def load_from_database(engine):
    genre_repository = GenreRepository(engine)
    topic_repository = TopicRepository(engine)
    explicit_repository = ExplicitRepository(engine)
    vocabulary_repository = VocabularyRepository(engine)
    emotion_repository = EmotionRepository(engine)
    topic_df = topic_repository.get_year_counts()
    return {
        "genre_df": genre_repository.get_year_counts(),
        "genre_topic_share_df": genre_repository.get_topic_shares(),
        "topic_df": topic_df,
        "topic_presence_df": topic_repository.get_presence_year_counts(),
        "explicit_df": explicit_repository.get_year_rates(),
        "explicit_breakdown_df": explicit_repository.get_breakdown_counts(),
        "emotion_df": emotion_repository.get_year_shares(),
        "genre_emotion_share_df": emotion_repository.get_genre_shares(),
        "sound_df": SoundRepository(engine).get_year_averages(),
        "economy_df": EconomyRepository(engine).get_year_averages(),
        "genre_distinctive_df": vocabulary_repository.get_genre_distinctive_terms(),
        "topic_distinctive_df": vocabulary_repository.get_topic_distinctive_terms(
            main_topics(topic_df)
        ),
        SHARED_WORDS: vocabulary_repository.get_shared_top_words(),
        "word_year_df": vocabulary_repository.get_word_year_counts(),
    }


def write_snapshot(data, snapshot_dir):
    snapshot_dir.mkdir(exist_ok=True)
    for name, value in data.items():
        df = pd.DataFrame({SHARED_WORD_COLUMN: value}) if name == SHARED_WORDS else value
        df.to_parquet(snapshot_dir / f"{name}{SNAPSHOT_SUFFIX}", index=False)


def read_snapshot(snapshot_dir):
    frames = {
        path.stem: pd.read_parquet(path)
        for path in snapshot_dir.glob(f"*{SNAPSHOT_SUFFIX}")
    }
    if not frames:
        raise FileNotFoundError(
            f"No snapshot in {snapshot_dir}. Run python dashboard/snapshot.py first"
        )
    return {**frames, SHARED_WORDS: frames[SHARED_WORDS][SHARED_WORD_COLUMN].tolist()}


if __name__ == "__main__":
    write_snapshot(load_from_database(build_engine()), SNAPSHOT_DIR)
