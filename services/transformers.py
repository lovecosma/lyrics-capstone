import logging
import re
import unicodedata
from collections.abc import Callable
from types import MappingProxyType
from typing import ClassVar

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_name(names):
    return names.str.strip().str.lower()


class TrackMerger:
    WORD_SEPARATOR = " "
    UNICODE_DECOMPOSITION_FORM = "NFKD"
    # Drops punctuation so "Don't Stop" and "Dont Stop" match
    PUNCTUATION_PATTERN = re.compile(r"[^\w\s]")
    # Collapses runs of spaces, tabs and newlines into one separator
    WHITESPACE_PATTERN = re.compile(r"\s+")
    # Splits "Drake feat. Rihanna" so the primary artist is "Drake"
    FEATURED_ARTIST_SEPARATOR = re.compile(r"\s+feat\.\s+", re.IGNORECASE)
    # Removes a bracketed credit like "Song (feat. Rihanna)" from a track name
    FEATURED_CREDIT_PATTERN = re.compile(
        r"\s*[(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s+(?P<artists>[^)\]]+)[)\]]",
        re.IGNORECASE,
    )
    # Removes remaster and remix tags like "Song (Remastered 2011)" or "Song - Remaster"
    VERSION_SUFFIX_PATTERN = re.compile(
        r"\s*[(\[]\s*(?:remaster(?:ed)?(?:\s+\d{4})?|remix)\s*[)\]]"
        r"|\s*-\s*remaster(?:ed)?(?:\s+\d{4})?$",
        re.IGNORECASE,
    )
    # Matches any bracketed or dashed suffix, like "Song (Live)" or "Song - Radio Edit"
    TITLE_SUFFIX_PATTERN = re.compile(r"\s*[(\[][^)\]]*[)\]]|\s+-\s+.*$")
    # Stripped one at a time, so "Song (Subtitle) [Radio Version]" also matches as
    # "Song Subtitle", which is how Billboard writes it
    TRAILING_BRACKET_PATTERN = re.compile(r"\s*[(\[][^)\]]*[)\]]\s*$")
    TRACK_SUFFIX_PATTERNS = (VERSION_SUFFIX_PATTERN, TITLE_SUFFIX_PATTERN)
    # Flags suffixes marking a different recording, like "Live" or "Acoustic"
    ALTERNATE_VERSION_PATTERN = re.compile(
        r"\b(?:remix|live|acoustic|unplugged|mix|instrumental|demo|sessions?|extended"
        r"|orchestral|synthesis|dub|broadway)\b"
        r"|12\""
        r"|\b(?:rock|pop|country|spanish) version\b",
        re.IGNORECASE,
    )
    BILLBOARD_ARTIST_ALIASES = MappingProxyType(
        {
            "Pink": "P!nk",
            "Dixie Chicks": "The Chicks",
            "Machine Gun Kelly": "mgk",
            "Machine Gun Kelly & Camila Cabello": "mgk & Camila Cabello",
        }
    )
    # Splits a credit like "Drake, Kanye West & Eminem" so it matches on "Drake"
    LEAD_ARTIST_SEPARATOR = re.compile(
        r"\s*(?:,|&|\b(?:featuring|with|and|x)\b|\b(?:feat|ft)\.)\s*", re.IGNORECASE
    )
    # Spellings that differ between sources, e.g. "A$AP Ferg" and "ASAP Ferg"
    ARTIST_CHARACTER_REPLACEMENTS = MappingProxyType({"$": "s"})
    # Drops a leading "the" so "The Weeknd" matches "Weeknd"
    LEADING_ARTICLE_PATTERN = re.compile(r"^the\s+")
    # Treats "and" like "&", which punctuation stripping already removed
    CONJUNCTION_PATTERN = re.compile(r"\band\b")
    BILLBOARD_ROW_COLUMN = "billboard_row"
    TRACK_NAME_COLUMN = "track_name"
    ARTIST_NAME_COLUMN = "artist_name"
    TRACK_MATCH_NAME_COLUMN = "track_match_name"
    ARTIST_MATCH_NAME_COLUMN = "artist_match_name"
    LEAD_ARTIST_MATCH_NAME_COLUMN = "lead_artist_match_name"
    MATCH_NAME_COLUMNS = (
        TRACK_MATCH_NAME_COLUMN,
        ARTIST_MATCH_NAME_COLUMN,
        LEAD_ARTIST_MATCH_NAME_COLUMN,
    )
    NAME_COLUMNS = (TRACK_NAME_COLUMN, ARTIST_NAME_COLUMN)
    CANDIDATE_COLUMN_SUFFIX = "_candidate"
    CANDIDATE_COLUMN_SUFFIXES = ("", CANDIDATE_COLUMN_SUFFIX)
    CANDIDATE_TRACK_NAME_COLUMN = f"{TRACK_NAME_COLUMN}{CANDIDATE_COLUMN_SUFFIX}"
    CANDIDATE_ARTIST_MATCH_NAME_COLUMN = (
        f"{ARTIST_MATCH_NAME_COLUMN}{CANDIDATE_COLUMN_SUFFIX}"
    )
    CANDIDATE_LEAD_ARTIST_MATCH_NAME_COLUMN = (
        f"{LEAD_ARTIST_MATCH_NAME_COLUMN}{CANDIDATE_COLUMN_SUFFIX}"
    )
    CANDIDATE_YEAR_COLUMN = "year"
    CANDIDATE_POPULARITY_COLUMN = "popularity"
    EXACT_ARTIST_MATCH_COLUMN = "is_exact_artist_match"
    TITLE_SUFFIX_COLUMN = "has_title_suffix"

    def transform(
        self, billboard_df: pd.DataFrame, candidate_track_df: pd.DataFrame
    ) -> pd.DataFrame:
        logger.info(
            "Matching %d Billboard rows to %d candidate tracks",
            len(billboard_df),
            len(candidate_track_df),
        )
        candidate_column_names = candidate_track_df.columns.drop(
            list(self.NAME_COLUMNS)
        )
        candidate_df = self._find_candidates(billboard_df, candidate_track_df)
        best_match_df = self._select_best_matches(candidate_df)[candidate_column_names]
        logger.info(
            "Matched %d of %d Billboard rows to candidate tracks",
            len(best_match_df),
            len(billboard_df),
        )
        return billboard_df.join(best_match_df)

    def _normalize_name(self, name: str) -> str:
        decomposed = unicodedata.normalize(
            self.UNICODE_DECOMPOSITION_FORM, name.casefold()
        )
        unaccented = "".join(
            char for char in decomposed if not unicodedata.combining(char)
        )
        return self.WHITESPACE_PATTERN.sub(
            self.WORD_SEPARATOR, self.PUNCTUATION_PATTERN.sub("", unaccented)
        ).strip()

    def _normalize_artist_name(self, artist_name: str) -> str:
        for character, replacement in self.ARTIST_CHARACTER_REPLACEMENTS.items():
            artist_name = artist_name.replace(character, replacement)
        unconjoined = self.CONJUNCTION_PATTERN.sub(
            self.WORD_SEPARATOR, self._normalize_name(artist_name)
        )
        return self.LEADING_ARTICLE_PATTERN.sub(
            "",
            self.WHITESPACE_PATTERN.sub(self.WORD_SEPARATOR, unconjoined).strip(),
        )

    def _get_lead_artist(self, artist_name: str) -> str:
        lead_artist, *_other_artists = self.LEAD_ARTIST_SEPARATOR.split(artist_name)
        # A name that starts with a separator word, like "X Ambassadors", has no lead
        return lead_artist or artist_name

    def _compact_name(self, name: str) -> str:
        return self.WHITESPACE_PATTERN.sub("", name)

    def get_primary_artist(self, artist_name: str) -> str:
        primary_artist, *_featured_artists = self.FEATURED_ARTIST_SEPARATOR.split(
            artist_name
        )
        return primary_artist

    def _get_track_match_names(self, track_name: str) -> list[str]:
        uncredited_name = self.FEATURED_CREDIT_PATTERN.sub("", track_name)
        unsuffixed_names = [
            suffix_pattern.sub("", uncredited_name)
            for suffix_pattern in self.TRACK_SUFFIX_PATTERNS
        ]
        return sorted(
            {
                self._compact_name(self._normalize_name(name))
                for name in (
                    *unsuffixed_names,
                    *self._strip_trailing_brackets(uncredited_name),
                )
            }
        )

    def _strip_trailing_brackets(self, track_name: str) -> list[str]:
        stripped_names = []
        while self.TRAILING_BRACKET_PATTERN.search(track_name):
            track_name = self.TRAILING_BRACKET_PATTERN.sub("", track_name)
            stripped_names.append(track_name)
        return stripped_names

    def _is_exact_artist_match(
        self, artist_match_name: str, candidate_artist_match_name: str
    ) -> bool:
        return self._compact_name(artist_match_name) == self._compact_name(
            candidate_artist_match_name
        )

    def _is_featured_artist_match(
        self, artist_match_name: str, candidate_artist_match_name: str
    ) -> bool:
        return artist_match_name.startswith(
            f"{candidate_artist_match_name}{self.WORD_SEPARATOR}"
        )

    def _add_match_names(self, df: pd.DataFrame) -> pd.DataFrame:
        primary_artists = (
            df[self.ARTIST_NAME_COLUMN]
            .fillna("")
            .map(self.get_primary_artist)
            .replace(self.BILLBOARD_ARTIST_ALIASES)
        )
        match_name_df = df.assign(
            **{
                self.TRACK_MATCH_NAME_COLUMN: df[self.TRACK_NAME_COLUMN]
                .fillna("")
                .map(self._get_track_match_names),
                self.ARTIST_MATCH_NAME_COLUMN: primary_artists.map(
                    self._normalize_artist_name
                ),
                self.LEAD_ARTIST_MATCH_NAME_COLUMN: primary_artists.map(
                    self._get_lead_artist
                ).map(self._normalize_artist_name),
            }
        ).explode(self.TRACK_MATCH_NAME_COLUMN)
        has_match_names = (
            match_name_df[list(self.MATCH_NAME_COLUMNS)].ne("").all(axis="columns")
        )
        return match_name_df[has_match_names]

    def _find_candidates(
        self, billboard_df: pd.DataFrame, candidate_track_df: pd.DataFrame
    ) -> pd.DataFrame:
        billboard_match_df = self._add_match_names(billboard_df)[
            [self.TRACK_NAME_COLUMN, *self.MATCH_NAME_COLUMNS]
        ].reset_index(names=self.BILLBOARD_ROW_COLUMN)
        return billboard_match_df.merge(
            self._add_match_names(candidate_track_df),
            on=self.TRACK_MATCH_NAME_COLUMN,
            suffixes=self.CANDIDATE_COLUMN_SUFFIXES,
        )

    def _match_artists(
        self,
        candidate_df: pd.DataFrame,
        is_artist_match: Callable[[str, str], bool],
    ) -> pd.Series:
        artist_match_name_pairs = zip(
            candidate_df[self.ARTIST_MATCH_NAME_COLUMN],
            candidate_df[self.CANDIDATE_ARTIST_MATCH_NAME_COLUMN],
        )
        return pd.Series(
            [
                is_artist_match(*artist_match_name_pair)
                for artist_match_name_pair in artist_match_name_pairs
            ],
            index=candidate_df.index,
        )

    def _is_matching_version(self, candidate_df: pd.DataFrame) -> pd.Series:
        candidate_version_suffixes = (
            candidate_df[self.CANDIDATE_TRACK_NAME_COLUMN]
            .fillna("")
            .str.findall(self.TITLE_SUFFIX_PATTERN)
            .str.join(self.WORD_SEPARATOR)
        )
        return ~candidate_version_suffixes.str.contains(
            self.ALTERNATE_VERSION_PATTERN
        ) | candidate_df[self.TRACK_NAME_COLUMN].str.contains(
            self.ALTERNATE_VERSION_PATTERN, na=False
        )

    def _has_title_suffix(self, candidate_df: pd.DataFrame) -> pd.Series:
        uncredited_names = (
            candidate_df[self.CANDIDATE_TRACK_NAME_COLUMN]
            .fillna("")
            .str.replace(self.FEATURED_CREDIT_PATTERN, "", regex=True)
        )
        return uncredited_names.str.contains(self.TITLE_SUFFIX_PATTERN)

    def _select_best_matches(self, candidate_df: pd.DataFrame) -> pd.DataFrame:
        is_exact_artist_match = self._match_artists(
            candidate_df, self._is_exact_artist_match
        )
        is_lead_artist_match = candidate_df[self.LEAD_ARTIST_MATCH_NAME_COLUMN].eq(
            candidate_df[self.CANDIDATE_LEAD_ARTIST_MATCH_NAME_COLUMN]
        )
        is_artist_match = (
            is_exact_artist_match
            | is_lead_artist_match
            | self._match_artists(candidate_df, self._is_featured_artist_match)
        )
        return (
            candidate_df.assign(
                **{
                    self.EXACT_ARTIST_MATCH_COLUMN: is_exact_artist_match,
                    self.TITLE_SUFFIX_COLUMN: self._has_title_suffix(candidate_df),
                }
            )[is_artist_match & self._is_matching_version(candidate_df)]
            .sort_values(
                [
                    self.EXACT_ARTIST_MATCH_COLUMN,
                    self.CANDIDATE_YEAR_COLUMN,
                    self.TITLE_SUFFIX_COLUMN,
                    self.CANDIDATE_POPULARITY_COLUMN,
                ],
                ascending=[False, True, True, False],
                kind="stable",
            )
            .drop_duplicates(subset=self.BILLBOARD_ROW_COLUMN)
            .set_index(self.BILLBOARD_ROW_COLUMN)
        )


class GenreTransformer:
    def transform(self, track_df):
        genre_df = (
            track_df["genre"]
            .pipe(normalize_name)
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .to_frame(name="name")
        )
        logger.info("Built %d genres", len(genre_df))
        return genre_df


class BroadGenreTransformer:
    NAME_COLUMN = "name"
    BROAD_GENRE_COLUMN = "broad_genre"

    def transform(self, genre_mapping_df):
        broad_genre_df = (
            genre_mapping_df[self.BROAD_GENRE_COLUMN]
            .str.strip()
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .to_frame(name=self.NAME_COLUMN)
        )
        logger.info("Built %d broad genres", len(broad_genre_df))
        return broad_genre_df


class GenreMappingTransformer:
    NAME_COLUMN = "name"
    GENRE_COLUMN = "genre"
    BROAD_GENRE_COLUMN = BroadGenreTransformer.BROAD_GENRE_COLUMN
    GENRE_ID_COLUMN = "genre_id"
    BROAD_GENRE_ID_COLUMN = "broad_genre_id"
    UNMAPPED_SEPARATOR = ", "

    def transform(self, db_genre_df, db_broad_genre_df, genre_mapping_df):
        genre_mapping_df = genre_mapping_df.assign(
            **{
                self.GENRE_COLUMN: normalize_name(genre_mapping_df[self.GENRE_COLUMN]),
                self.BROAD_GENRE_COLUMN: genre_mapping_df[
                    self.BROAD_GENRE_COLUMN
                ].str.strip(),
            }
        )
        mapped_genre_df = (
            db_genre_df[[self.GENRE_ID_COLUMN, self.NAME_COLUMN]]
            .rename(columns={self.NAME_COLUMN: self.GENRE_COLUMN})
            .merge(genre_mapping_df, how="inner", on=self.GENRE_COLUMN)
            .merge(
                db_broad_genre_df.rename(
                    columns={self.NAME_COLUMN: self.BROAD_GENRE_COLUMN}
                ),
                how="inner",
                on=self.BROAD_GENRE_COLUMN,
            )[[self.GENRE_ID_COLUMN, self.BROAD_GENRE_ID_COLUMN]]
            .drop_duplicates(subset=[self.GENRE_ID_COLUMN])
        )
        is_mapped = db_genre_df[self.GENRE_ID_COLUMN].isin(
            mapped_genre_df[self.GENRE_ID_COLUMN]
        )
        unmapped_genres = sorted(db_genre_df.loc[~is_mapped, self.NAME_COLUMN])
        if unmapped_genres:
            logger.warning(
                "No broad genre for %d genres: %s",
                len(unmapped_genres),
                self.UNMAPPED_SEPARATOR.join(unmapped_genres),
            )
        logger.info(
            "Mapped %d of %d genres to a broad genre",
            len(mapped_genre_df),
            len(db_genre_df),
        )
        return mapped_genre_df


class ChartTransformer:
    def transform(self, track_df: pd.DataFrame) -> pd.DataFrame:
        chart_df = (
            track_df["chart_year"]
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
            .to_frame(name="year")
        )
        chart_df["year"] = chart_df["year"].astype(int)
        logger.info("Built %d charts", len(chart_df))
        return chart_df


class TrackTransformer:
    SONG_KEY_COLUMNS = ("track_name", "artist_name")
    CHART_YEAR_COLUMN = "chart_year"
    COLUMN_RENAMES = MappingProxyType({"track_name": "title"})
    TRACK_COLUMNS = (
        "title",
        "artist_name",
        "lyrics",
        "danceability",
        "energy",
        "speechiness",
        "acousticness",
        "instrumentalness",
        "liveness",
        "valence",
        "loudness",
        "tempo",
        "key",
        "mode",
        "time_signature",
        "duration_ms",
    )
    INTEGER_COLUMNS = ("key", "mode", "time_signature", "duration_ms")
    NULLABLE_INTEGER_DTYPE = "Int64"

    def transform(self, track_df: pd.DataFrame) -> pd.DataFrame:
        song_df = (
            track_df.sort_values(self.CHART_YEAR_COLUMN, kind="stable")
            .drop_duplicates(subset=list(self.SONG_KEY_COLUMNS))
            .rename(columns=self.COLUMN_RENAMES)[list(self.TRACK_COLUMNS)]
            .astype(dict.fromkeys(self.INTEGER_COLUMNS, self.NULLABLE_INTEGER_DTYPE))
            .reset_index(drop=True)
        )
        logger.info(
            "Built %d unique tracks from %d chart rows", len(song_df), len(track_df)
        )
        return song_df


class TrackGenreTransformer:
    def transform(self, db_track_df, db_genre_df, source_track_df):
        track_df = db_track_df.merge(
            source_track_df[["track_name", "artist_name", "genre"]],
            how="left",
            left_on=["title", "artist_name"],
            right_on=["track_name", "artist_name"],
        ).drop(columns=["track_name"])
        track_df["genre"] = normalize_name(track_df["genre"])
        track_genre_df = track_df.merge(
            db_genre_df, how="inner", left_on="genre", right_on="name"
        ).drop(columns=["genre", "name"])
        track_genre_df = track_genre_df[["track_id", "genre_id"]].drop_duplicates()
        logger.info(
            "Linked %d of %d tracks to a genre",
            track_genre_df["track_id"].nunique(),
            len(db_track_df),
        )
        return track_genre_df


class ChartTrackTransformer:
    def transform(
        self,
        db_track_df: pd.DataFrame,
        db_chart_df: pd.DataFrame,
        source_track_df: pd.DataFrame,
    ) -> pd.DataFrame:
        track_df = db_track_df.merge(
            source_track_df[["track_name", "artist_name", "chart_year", "rank"]],
            how="left",
            left_on=["title", "artist_name"],
            right_on=["track_name", "artist_name"],
        ).drop(columns=["track_name"])
        chart_track_df = track_df.merge(
            db_chart_df, how="inner", left_on="chart_year", right_on="year"
        ).drop(columns=["chart_year", "year"])
        chart_track_df = chart_track_df[
            ["track_id", "chart_id", "rank"]
        ].drop_duplicates()
        logger.info(
            "Linked %d of %d tracks to %d chart entries",
            chart_track_df["track_id"].nunique(),
            len(db_track_df),
            len(chart_track_df),
        )
        return chart_track_df


class DroppedGVariantBuilder:
    GERUND_SUFFIX = "ing"
    # LyricsTokenizer turns "lovin'" into "lovin", so "loving" also matches as "lovin"
    DROPPED_G_SUFFIX = "in"
    # Skips one-syllable words like "king" and "sing" that aren't gerunds
    MIN_GERUND_STEM_LENGTH = 2

    def build(self, lexicon_df, word_column, lexicon_words):
        words = lexicon_df[word_column]
        stems = words.str.removesuffix(self.GERUND_SUFFIX)
        variants = stems + self.DROPPED_G_SUFFIX
        is_gerund = words.str.endswith(self.GERUND_SUFFIX) & stems.str.len().ge(
            self.MIN_GERUND_STEM_LENGTH
        )
        is_new_variant = is_gerund & ~variants.isin(lexicon_words)
        return lexicon_df[is_new_variant].assign(
            **{word_column: variants[is_new_variant]}
        )


class EmotionLexiconTransformer:
    WORD_COLUMN = "word"
    EMOTION_COLUMN = "emotion"
    ASSOCIATION_COLUMN = "association"
    LEXICON_COLUMNS = (WORD_COLUMN, EMOTION_COLUMN, ASSOCIATION_COLUMN)
    ASSOCIATED = 1

    def __init__(self, variant_builder):
        self._variant_builder = variant_builder

    def transform(self, lexicon_df):
        lexicon_df = lexicon_df.dropna(subset=[self.EMOTION_COLUMN])
        lexicon_df = lexicon_df.assign(
            **{
                self.WORD_COLUMN: normalize_name(lexicon_df[self.WORD_COLUMN]),
                self.EMOTION_COLUMN: lexicon_df[self.EMOTION_COLUMN].str.strip(),
            }
        )
        associated_df = lexicon_df[
            lexicon_df[self.ASSOCIATION_COLUMN].eq(self.ASSOCIATED)
        ][[self.WORD_COLUMN, self.EMOTION_COLUMN]]
        word_emotion_df = pd.concat(
            [
                associated_df,
                self._variant_builder.build(
                    associated_df,
                    self.WORD_COLUMN,
                    frozenset(lexicon_df[self.WORD_COLUMN]),
                ),
            ],
            ignore_index=True,
        ).drop_duplicates()
        logger.info(
            "Built %d word emotions for %d words",
            len(word_emotion_df),
            word_emotion_df[self.WORD_COLUMN].nunique(),
        )
        return word_emotion_df


class WordVadTransformer:
    WORD_COLUMN = "word"
    VALENCE_COLUMN = "valence"
    AROUSAL_COLUMN = "arousal"
    DOMINANCE_COLUMN = "dominance"
    LEXICON_COLUMNS = (WORD_COLUMN, VALENCE_COLUMN, AROUSAL_COLUMN, DOMINANCE_COLUMN)

    def __init__(self, variant_builder):
        self._variant_builder = variant_builder

    def transform(self, lexicon_df):
        lexicon_df = lexicon_df.dropna()
        lexicon_df = lexicon_df.assign(
            **{self.WORD_COLUMN: normalize_name(lexicon_df[self.WORD_COLUMN])}
        ).drop_duplicates(subset=[self.WORD_COLUMN])
        word_vad_df = pd.concat(
            [
                lexicon_df,
                self._variant_builder.build(
                    lexicon_df,
                    self.WORD_COLUMN,
                    frozenset(lexicon_df[self.WORD_COLUMN]),
                ),
            ],
            ignore_index=True,
        )[list(self.LEXICON_COLUMNS)]
        logger.info("Built VAD scores for %d words", len(word_vad_df))
        return word_vad_df


class EmotionTransformer:
    EMOTION_COLUMN = EmotionLexiconTransformer.EMOTION_COLUMN
    NAME_COLUMN = "name"
    DISPLAY_NAME_COLUMN = "display_name"

    def transform(self, word_emotion_df):
        emotion_df = (
            word_emotion_df[self.EMOTION_COLUMN]
            .drop_duplicates()
            .sort_values()
            .reset_index(drop=True)
            .to_frame(name=self.NAME_COLUMN)
        )
        emotion_df[self.DISPLAY_NAME_COLUMN] = emotion_df[self.NAME_COLUMN].str.title()
        logger.info("Built %d emotions", len(emotion_df))
        return emotion_df


class WordEmotionTransformer:
    WORD_COLUMN = EmotionLexiconTransformer.WORD_COLUMN
    EMOTION_COLUMN = EmotionLexiconTransformer.EMOTION_COLUMN
    EMOTION_NAME_COLUMN = EmotionTransformer.NAME_COLUMN
    EMOTION_ID_COLUMN = "emotion_id"
    WORD_EMOTION_COLUMNS = (WORD_COLUMN, EMOTION_ID_COLUMN)

    def transform(self, db_emotion_df, word_emotion_df):
        word_emotion_df = word_emotion_df.merge(
            db_emotion_df,
            how="inner",
            left_on=self.EMOTION_COLUMN,
            right_on=self.EMOTION_NAME_COLUMN,
        )[list(self.WORD_EMOTION_COLUMNS)]
        logger.info("Linked %d word emotions", len(word_emotion_df))
        return word_emotion_df


class ProfanityWordTransformer:
    TEXT_COLUMN = "text"
    WORD_COLUMN = "word"
    CATEGORY_SOURCE_COLUMN = "category_1"
    CATEGORY_COLUMN = "category"
    PROFANITY_COLUMNS = (
        WORD_COLUMN,
        "canonical_form_1",
        "canonical_form_2",
        "canonical_form_3",
        CATEGORY_COLUMN,
        "severity_rating",
        "severity_description",
    )

    def transform(self, profanity_df):
        profanity_df = profanity_df.rename(
            columns={
                self.TEXT_COLUMN: self.WORD_COLUMN,
                self.CATEGORY_SOURCE_COLUMN: self.CATEGORY_COLUMN,
            }
        )
        # Lowercased only; lyric words are lowercase, and stripping punctuation would merge
        # spellings like "a_s_s" into ordinary words
        profanity_df = (
            profanity_df.assign(
                **{
                    self.WORD_COLUMN: profanity_df[self.WORD_COLUMN]
                    .str.lower()
                    .str.strip()
                }
            )
            .dropna(subset=[self.WORD_COLUMN])
            .drop_duplicates(subset=[self.WORD_COLUMN])[list(self.PROFANITY_COLUMNS)]
        )
        logger.info("Built %d profanity words", len(profanity_df))
        return profanity_df


class LookupTableTransformer:
    KEY_COLUMN: ClassVar[str]
    COLUMNS: ClassVar[tuple[str, ...]]
    ROW_DESCRIPTION: ClassVar[str]

    def transform(self, lookup_df: pd.DataFrame) -> pd.DataFrame:
        lookup_df = (
            lookup_df[list(self.COLUMNS)]
            .drop_duplicates(subset=[self.KEY_COLUMN])
            .dropna()
        )
        logger.info("Built %d %s", len(lookup_df), self.ROW_DESCRIPTION)
        return lookup_df


class EconomicIndicatorTransformer(LookupTableTransformer):
    KEY_COLUMN = "code"
    COLUMNS = (KEY_COLUMN, "display_name", "unit", "description")
    ROW_DESCRIPTION = "economic indicators"


class EconomicObservationTransformer:
    CODE_COLUMN = EconomicIndicatorTransformer.KEY_COLUMN
    INDICATOR_ID_COLUMN = "economic_indicator_id"
    OBSERVATION_DATE_COLUMN = "observation_date"
    VALUE_COLUMN = "value"
    OBSERVATION_COLUMNS = (INDICATOR_ID_COLUMN, OBSERVATION_DATE_COLUMN, VALUE_COLUMN)

    def transform(self, db_indicator_df, observation_df):
        observation_df = observation_df.dropna(subset=[self.VALUE_COLUMN]).merge(
            db_indicator_df, how="inner", on=self.CODE_COLUMN
        )[list(self.OBSERVATION_COLUMNS)]
        logger.info(
            "Linked %d observations to %d economic indicators",
            len(observation_df),
            observation_df[self.INDICATOR_ID_COLUMN].nunique(),
        )
        return observation_df


class TopicsTransformer(LookupTableTransformer):
    KEY_COLUMN = "name"
    COLUMNS = (KEY_COLUMN, "display_name", "description")
    ROW_DESCRIPTION = "topics"
