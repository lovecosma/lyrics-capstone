"""Exports the dashboard's data to Parquet files, so the app can run without a database.

The DAG's export_dashboard_snapshot task runs this after every pipeline run.
To export by hand: python dashboard/snapshot.py
"""

import shutil
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
# Sibling folders used to swap a new snapshot in whole, so a failed export never leaves a mix
STAGING_SUFFIX = ".staging"
PREVIOUS_SUFFIX = ".previous"
SHARED_WORDS = "shared_words"
SHARED_WORD_COLUMN = "word"
SNAPSHOT_NAMES = (
    "genre_df",
    "genre_topic_share_df",
    "topic_df",
    "topic_presence_df",
    "explicit_df",
    "explicit_breakdown_df",
    "emotion_df",
    "genre_emotion_share_df",
    "sound_df",
    "economy_df",
    "genre_distinctive_df",
    "topic_distinctive_df",
    SHARED_WORDS,
    "word_year_df",
)


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
    mismatched = sorted(set(data) ^ set(SNAPSHOT_NAMES))
    if mismatched:
        raise ValueError(f"Snapshot datasets don't match SNAPSHOT_NAMES: {mismatched}")
    staging_dir = snapshot_dir.with_name(f"{snapshot_dir.name}{STAGING_SUFFIX}")
    previous_dir = snapshot_dir.with_name(f"{snapshot_dir.name}{PREVIOUS_SUFFIX}")
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir()
    for name, value in data.items():
        df = pd.DataFrame({SHARED_WORD_COLUMN: value}) if name == SHARED_WORDS else value
        df.to_parquet(staging_dir / f"{name}{SNAPSHOT_SUFFIX}", index=False)
    shutil.rmtree(previous_dir, ignore_errors=True)
    if snapshot_dir.exists():
        snapshot_dir.rename(previous_dir)
    staging_dir.rename(snapshot_dir)
    shutil.rmtree(previous_dir, ignore_errors=True)


def read_snapshot(snapshot_dir):
    paths = {name: snapshot_dir / f"{name}{SNAPSHOT_SUFFIX}" for name in SNAPSHOT_NAMES}
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Snapshot in {snapshot_dir} is missing {', '.join(missing)}. "
            "Run python dashboard/snapshot.py first"
        )
    frames = {name: pd.read_parquet(path) for name, path in paths.items()}
    return {**frames, SHARED_WORDS: frames[SHARED_WORDS][SHARED_WORD_COLUMN].tolist()}


if __name__ == "__main__":
    engine = build_engine()
    try:
        write_snapshot(load_from_database(engine), SNAPSHOT_DIR)
    finally:
        engine.dispose()
