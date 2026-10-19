import csv
import logging
import re
from pathlib import Path

import pandas as pd
from psycopg import sql
from sqlalchemy import text

from transformers import (
    BroadGenreTransformer,
    ChartTrackTransformer,
    ChartTransformer,
    DroppedGVariantBuilder,
    EconomicIndicatorTransformer,
    EconomicObservationTransformer,
    EmotionLexiconTransformer,
    EmotionTransformer,
    GenreMappingTransformer,
    TopicsTransformer,
    TrackMerger,
    TrackTransformer,
    WordEmotionTransformer,
    WordVadTransformer,
)

LYRICS_SCHEMA = "billboard_lyrics"
TRACK_ID_COLUMN = "track_id"
TRACK_TABLE = "track"
GENRE_TABLE = "genre"
BROAD_GENRE_TABLE = "broad_genre"
TRACK_GENRE_TABLE = "track_genre"
CHART_TABLE = "chart"
CHART_TRACK_TABLE = "chart_track"
TOPIC_TABLE = "topic"
LYRICS_TOPIC_TABLE = "lyrics_topic"
LYRICS_METRIC_TABLE = "lyrics_metric"
LYRICS_NGRAM_METRIC_TABLE = "lyrics_ngram_metric"
EMOTION_TABLE = "emotion"
WORD_EMOTION_TABLE = "word_emotion"
WORD_VAD_TABLE = "word_vad"
ECONOMIC_INDICATOR_TABLE = "economic_indicator"
ECONOMIC_OBSERVATION_TABLE = "economic_observation"

logger = logging.getLogger(__name__)


class Extractor:
    COMMENT_PREFIX = "#"
    TRACK_IDS_PARAMETER = "track_ids"

    def __init__(self, connection):
        self._connection = connection

    def extract_from_csv(self, file_path, **read_csv_options) -> pd.DataFrame:
        logger.info("Extracting rows from CSV at %s", file_path)
        df = pd.read_csv(file_path, **read_csv_options)
        logger.info("Extracted %d rows from CSV", len(df))
        return df

    def extract_from_db(self, table_name):
        logger.info("Extracting %s.%s from the database", LYRICS_SCHEMA, table_name)
        query = f"select * from {LYRICS_SCHEMA}.{table_name}"
        df = pd.read_sql_query(query, con=self._connection)
        logger.info("Extracted %d rows from %s.%s", len(df), LYRICS_SCHEMA, table_name)
        return df

    def extract_tracks(self, track_ids):
        logger.info("Extracting %d tracks from the database", len(track_ids))
        query = text(
            f"select * from {LYRICS_SCHEMA}.{TRACK_TABLE}"
            f" where {TRACK_ID_COLUMN} = any(:{self.TRACK_IDS_PARAMETER})"
        )
        track_df = pd.read_sql_query(
            query,
            con=self._connection,
            params={self.TRACK_IDS_PARAMETER: list(track_ids)},
        )
        logger.info("Extracted %d tracks", len(track_df))
        return track_df

    def extract_word_list(self, file_path):
        logger.info("Extracting word list from %s", file_path)
        with open(file_path, encoding="utf-8") as word_list_file:
            lines = (line.strip() for line in word_list_file)
            words = frozenset(
                line
                for line in lines
                if line and not line.startswith(self.COMMENT_PREFIX)
            )
        logger.info("Extracted %d words from %s", len(words), file_path)
        return words


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


class FredExtractor(Extractor):
    SERIES_FILE_SUFFIX = ".csv"
    DATE_COLUMN = EconomicObservationTransformer.OBSERVATION_DATE_COLUMN
    CODE_COLUMN = EconomicObservationTransformer.CODE_COLUMN
    VALUE_COLUMN = EconomicObservationTransformer.VALUE_COLUMN
    # FRED marks a missing observation with "."
    MISSING_VALUE = "."

    def extract_series(self, directory_path, codes):
        logger.info(
            "Extracting %d FRED series from directory at %s", len(codes), directory_path
        )
        series_df = pd.concat(
            [self._extract_one_series(directory_path, code) for code in codes],
            ignore_index=True,
        )
        logger.info("Extracted %d FRED observations", len(series_df))
        return series_df

    def _extract_one_series(self, directory_path, code):
        file_path = Path(directory_path) / f"{code}{self.SERIES_FILE_SUFFIX}"
        return (
            self.extract_from_csv(
                file_path,
                parse_dates=[self.DATE_COLUMN],
                na_values=[self.MISSING_VALUE],
            )
            .rename(columns={code: self.VALUE_COLUMN})
            .assign(**{self.CODE_COLUMN: code})
        )


class NrcLexiconExtractor(Extractor):
    FIELD_SEPARATOR = "\t"
    # Only empty fields are missing; words like "null" and "nan" are real entries
    MISSING_VALUES = ("",)

    def extract_lexicon(self, file_path, column_names):
        return self.extract_from_csv(
            file_path,
            sep=self.FIELD_SEPARATOR,
            header=None,
            names=list(column_names),
            quoting=csv.QUOTE_NONE,
            keep_default_na=False,
            na_values=list(self.MISSING_VALUES),
        )


class Loader:
    def __init__(self, connection):
        self._connection = connection

    def load_to_db(self, df, table_name):
        logger.info("Loading %d rows into %s.%s", len(df), LYRICS_SCHEMA, table_name)
        result = df.to_sql(
            table_name,
            self._connection,
            schema=LYRICS_SCHEMA,
            if_exists="append",
            index=False,
        )
        logger.info("Loaded %s.%s", LYRICS_SCHEMA, table_name)
        return result

    def copy_to_db(self, df, table_name):
        logger.info("Copying %d rows into %s.%s", len(df), LYRICS_SCHEMA, table_name)
        copy_statement = sql.SQL("copy {table} ({columns}) from stdin").format(
            table=sql.Identifier(LYRICS_SCHEMA, table_name),
            columns=sql.SQL(", ").join(map(sql.Identifier, df.columns)),
        )
        driver_connection = self._driver_connection()
        with driver_connection.cursor() as cursor, cursor.copy(copy_statement) as copy:
            for row in self._to_rows(df):
                copy.write_row(row)
        logger.info("Copied %s.%s", LYRICS_SCHEMA, table_name)

    def update_db(self, df, table_name, key_column):
        logger.info("Updating %d rows in %s.%s", len(df), LYRICS_SCHEMA, table_name)
        value_columns = df.columns.drop(key_column)
        update_statement = sql.SQL(
            "update {table} set {assignments} where {key} = %s"
        ).format(
            table=sql.Identifier(LYRICS_SCHEMA, table_name),
            assignments=sql.SQL(", ").join(
                sql.SQL("{column} = %s").format(column=sql.Identifier(column))
                for column in value_columns
            ),
            key=sql.Identifier(key_column),
        )
        with self._driver_connection().cursor() as cursor:
            cursor.executemany(
                update_statement, self._to_rows(df[[*value_columns, key_column]])
            )
        logger.info("Updated %s.%s", LYRICS_SCHEMA, table_name)

    def _driver_connection(self):
        return self._connection.connection.driver_connection

    def _to_rows(self, df):
        return (
            df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
        )


class TrackProcessor:
    # The CSV's unnamed index and Spotify's own track id, which would clash with ours
    SPOTIFY_ID_COLUMNS = ("Unnamed: 0", "track_id")

    def __init__(self, extractor, loader, billboard_directory_path, spotify_csv_path):
        self._extractor = extractor
        self._loader = loader
        self._billboard_directory_path = billboard_directory_path
        self._spotify_csv_path = spotify_csv_path

    def process(self):
        logger.info("Starting track ETL")
        billboard_df = self._extractor.extract_from_directory(
            self._billboard_directory_path
        )
        spotify_df = self._extractor.extract_from_csv(self._spotify_csv_path).drop(
            columns=list(self.SPOTIFY_ID_COLUMNS)
        )
        source_track_df = TrackMerger().transform(billboard_df, spotify_df)

        self._loader.load_to_db(
            ChartTransformer().transform(source_track_df), CHART_TABLE
        )
        self._loader.load_to_db(
            TrackTransformer().transform(source_track_df), TRACK_TABLE
        )

        chart_track_df = ChartTrackTransformer().transform(
            self._extractor.extract_from_db(TRACK_TABLE),
            self._extractor.extract_from_db(CHART_TABLE),
            source_track_df,
        )
        self._loader.load_to_db(chart_track_df, CHART_TRACK_TABLE)
        logger.info("Completed track ETL")


class TopicProcessor:
    def __init__(self, extractor, loader, topic_csv_path):
        self._extractor = extractor
        self._loader = loader
        self._topic_csv_path = topic_csv_path

    def process(self):
        logger.info("Starting topic ETL")
        topic_df = self._extractor.extract_from_csv(self._topic_csv_path)
        self._loader.load_to_db(TopicsTransformer().transform(topic_df), TOPIC_TABLE)
        logger.info("Completed topic ETL")


class GenreMappingProcessor:
    def __init__(self, extractor, loader, genre_mapping_csv_path):
        self._extractor = extractor
        self._loader = loader
        self._genre_mapping_csv_path = genre_mapping_csv_path

    def process(self):
        logger.info("Starting genre mapping ETL")
        genre_mapping_df = self._extractor.extract_from_csv(
            self._genre_mapping_csv_path
        )
        self._loader.load_to_db(
            self._select_new_broad_genres(genre_mapping_df), BROAD_GENRE_TABLE
        )

        mapped_genre_df = GenreMappingTransformer().transform(
            self._extractor.extract_from_db(GENRE_TABLE),
            self._extractor.extract_from_db(BROAD_GENRE_TABLE),
            genre_mapping_df,
        )
        self._loader.update_db(
            mapped_genre_df, GENRE_TABLE, GenreMappingTransformer.GENRE_ID_COLUMN
        )
        logger.info("Completed genre mapping ETL")

    def _select_new_broad_genres(self, genre_mapping_df):
        broad_genre_df = BroadGenreTransformer().transform(genre_mapping_df)
        is_loaded = broad_genre_df[BroadGenreTransformer.NAME_COLUMN].isin(
            self._extractor.extract_from_db(BROAD_GENRE_TABLE)[
                BroadGenreTransformer.NAME_COLUMN
            ]
        )
        return broad_genre_df[~is_loaded]


class EmotionLexiconProcessor:
    def __init__(self, extractor, loader, emotion_lexicon_path, vad_lexicon_path):
        self._extractor = extractor
        self._loader = loader
        self._emotion_lexicon_path = emotion_lexicon_path
        self._vad_lexicon_path = vad_lexicon_path

    def process(self):
        logger.info("Starting emotion lexicon ETL")
        lexicon_df = self._extractor.extract_lexicon(
            self._emotion_lexicon_path, EmotionLexiconTransformer.LEXICON_COLUMNS
        )
        vad_df = self._extractor.extract_lexicon(
            self._vad_lexicon_path, WordVadTransformer.LEXICON_COLUMNS
        )
        variant_builder = DroppedGVariantBuilder()
        word_emotion_df = EmotionLexiconTransformer(variant_builder).transform(
            lexicon_df
        )

        self._loader.load_to_db(
            EmotionTransformer().transform(word_emotion_df), EMOTION_TABLE
        )
        self._loader.load_to_db(
            WordVadTransformer(variant_builder).transform(vad_df), WORD_VAD_TABLE
        )

        word_emotion_df = WordEmotionTransformer().transform(
            self._extractor.extract_from_db(EMOTION_TABLE), word_emotion_df
        )
        self._loader.load_to_db(word_emotion_df, WORD_EMOTION_TABLE)
        logger.info("Completed emotion lexicon ETL")


class EconomicIndicatorProcessor:
    def __init__(
        self, extractor, loader, economic_indicator_csv_path, fred_directory_path
    ):
        self._extractor = extractor
        self._loader = loader
        self._economic_indicator_csv_path = economic_indicator_csv_path
        self._fred_directory_path = fred_directory_path

    def process(self):
        logger.info("Starting economic indicator ETL")
        indicator_df = EconomicIndicatorTransformer().transform(
            self._extractor.extract_from_csv(self._economic_indicator_csv_path)
        )
        observation_df = self._extractor.extract_series(
            self._fred_directory_path,
            indicator_df[EconomicIndicatorTransformer.KEY_COLUMN].tolist(),
        )

        self._loader.load_to_db(indicator_df, ECONOMIC_INDICATOR_TABLE)

        observation_df = EconomicObservationTransformer().transform(
            self._extractor.extract_from_db(ECONOMIC_INDICATOR_TABLE), observation_df
        )
        self._loader.load_to_db(observation_df, ECONOMIC_OBSERVATION_TABLE)
        logger.info("Completed economic indicator ETL")
