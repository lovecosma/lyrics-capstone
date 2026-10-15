import logging
import re
from pathlib import Path

import pandas as pd

from transformers import (
    ChartTrackTransformer,
    ChartTransformer,
    GenreTransformer,
    TopicsTransformer,
    TrackGenreTransformer,
    TrackMerger,
    TrackTransformer,
)

LYRICS_SCHEMA = "billboard_lyrics"

logger = logging.getLogger(__name__)


class Extractor:
    def __init__(self, engine):
        self._engine = engine

    def extract_from_csv(self, file_path):
        logger.info("Extracting songs from CSV at %s", file_path)
        df = pd.read_csv(file_path)
        logger.info("Extracted %d rows from CSV", len(df))
        return df

    def extract_from_db(self, table_name):
        logger.info("Extracting %s.%s from the database", LYRICS_SCHEMA, table_name)
        sql = f"select * from {LYRICS_SCHEMA}.{table_name}"
        df = pd.read_sql_query(sql, con=self._engine)
        logger.info("Extracted %d rows from %s.%s", len(df), LYRICS_SCHEMA, table_name)
        return df


class BillboardExtractor(Extractor):
    LYRICS_FILE_GLOB = "billboard-year-end-*-lyrics.csv"
    LYRICS_COLUMNS = ("rank", "track_name", "artist_name", "lyrics")
    CHART_YEAR_PATTERN = re.compile(
        r"billboard-year-end-(?P<chart_year>\d{4})-lyrics\.csv$"
    )
    TRACK_NAME_COLUMN = "track_name"
    ARTIST_NAME_COLUMN = "artist_name"
    LYRICS_COLUMN = "lyrics"
    NAME_COLUMNS = (TRACK_NAME_COLUMN, ARTIST_NAME_COLUMN)

    def extract_from_directory(self, directory_path):
        logger.info(
            "Extracting songs from CSV files in directory at %s", directory_path
        )
        file_paths = sorted(Path(directory_path).glob(self.LYRICS_FILE_GLOB))
        df = pd.concat(map(self._extract_chart_lyrics, file_paths), ignore_index=True)
        logger.info("Extracted %d rows from %d CSV files", len(df), len(file_paths))
        return df

    def _extract_chart_lyrics(self, file_path) -> pd.DataFrame:
        return (
            self.extract_from_csv(file_path)
            .set_axis(self.LYRICS_COLUMNS, axis="columns")
            .pipe(self._strip_names)
            .dropna(subset=[self.LYRICS_COLUMN])
            .assign(chart_year=self._get_chart_year(file_path))
        )

    def _strip_names(self, df):
        return df.assign(
            **{
                name_column: df[name_column].str.strip()
                for name_column in self.NAME_COLUMNS
            }
        )

    def _get_chart_year(self, file_path):
        chart_year_match = self.CHART_YEAR_PATTERN.search(file_path.name)
        if chart_year_match is None:
            raise ValueError(f"No chart year in file name: {file_path}")
        return int(chart_year_match["chart_year"])


class Loader:
    def __init__(self, engine):
        self._engine = engine

    def load_to_db(self, df, table_name):
        logger.info("Loading %d rows into %s.%s", len(df), LYRICS_SCHEMA, table_name)
        result = df.to_sql(
            table_name,
            self._engine,
            schema=LYRICS_SCHEMA,
            if_exists="append",
            index=False,
        )
        logger.info("Loaded %s.%s", LYRICS_SCHEMA, table_name)
        return result


class ETLProcessor:
    def __init__(self, engine, billboard_directory_path, spotify_csv_path, topic_csv_path):
        self._extractor = BillboardExtractor(engine)
        self._loader = Loader(engine)
        self._billboard_directory_path = billboard_directory_path
        self._spotify_csv_path = spotify_csv_path
        self._topic_csv_path = topic_csv_path

    def _extract(self):
        billboard_df = self._extractor.extract_from_directory(
            self._billboard_directory_path
        )
        spotify_df = self._extractor.extract_from_csv(self._spotify_csv_path)
        topic_df = self._extractor.extract_from_csv(self._topic_csv_path)
        return billboard_df, spotify_df, topic_df

    def process(self):
        logger.info("Starting song ETL process")
        billboard_df, spotify_df, topic_df = self._extract()
        source_track_df = TrackMerger().transform(billboard_df, spotify_df)
        genre_df = GenreTransformer().transform(source_track_df)
        chart_df = ChartTransformer().transform(source_track_df)
        track_df = TrackTransformer().transform(source_track_df)
        topic_df = TopicsTransformer().transform(topic_df)

        self._loader.load_to_db(genre_df, "genre")
        self._loader.load_to_db(chart_df, "chart")
        self._loader.load_to_db(topic_df, "topic")
        self._loader.load_to_db(track_df, "track")

        db_track_df = self._extractor.extract_from_db("track")
        db_genre_df = self._extractor.extract_from_db("genre")
        db_chart_df = self._extractor.extract_from_db("chart")

        track_genre_df = TrackGenreTransformer().transform(
            db_track_df, db_genre_df, source_track_df
        )
        
        chart_track_df = ChartTrackTransformer().transform(
            db_track_df, db_chart_df, source_track_df
        )

        self._loader.load_to_db(track_genre_df, "track_genre")
        self._loader.load_to_db(chart_track_df, "chart_track")

        logger.info("Completed song ETL process")
