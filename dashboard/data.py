import pandas as pd

LYRICS_SCHEMA = "billboard_lyrics"
TOPIC_ANALYSIS_VERSION = "v1"
TOPIC_PRESENCE_THRESHOLD = 0.7
LYRICS_ANALYSIS_VERSION = "v3"
PERCENT = 100
WORDS_PER_RATE = 1000
MAX_NGRAM_LENGTH = 2
VOCABULARY_GENRES = (
    "Pop",
    "Hip-Hop/Rap",
    "R&B/Soul",
    "Country/Folk",
    "Rock/Alternative",
)
MIN_DISTINCTIVE_SHARE = 8
DISTINCTIVE_SMOOTHING_POINTS = 0.5
DISTINCTIVE_TERM_COUNT = 10
SHARED_WORD_RANK = 12
PROFANITY_TERM = "[strong profanity]"


class GenreRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_counts(self):
        sql = f"""
    select year, broad_genre, count(*)::int as entry_count
    from {LYRICS_SCHEMA}.chart_entry
    where broad_genre is not null
    group by year, broad_genre
    """
        return pd.read_sql(sql, self._engine)

    def get_topic_shares(self):
        sql = f"""
    with genre_topic as (
      select broad_genre, main_theme as main_topic, sum(entry_count) as entry_count
      from {LYRICS_SCHEMA}.genre_theme_year_count
      where topic_analysis_version = %(analysis_version)s
        and broad_genre is not null
      group by broad_genre, main_theme
    ),
    with_totals as (
      select
        *,
        sum(entry_count) over (partition by broad_genre) as genre_song_count,
        sum(entry_count) over (partition by main_topic) as topic_song_count,
        sum(entry_count) over () as song_count
      from genre_topic
    )
    select
      broad_genre,
      main_topic,
      genre_song_count::int as genre_song_count,
      entry_count * %(percent)s::float / genre_song_count as genre_share,
      topic_song_count * %(percent)s::float / song_count as average_share
    from with_totals
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={"analysis_version": TOPIC_ANALYSIS_VERSION, "percent": PERCENT},
        )


class TopicRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_counts(self):
        sql = f"""
    select year, main_theme as main_topic, sum(entry_count)::int as entry_count
    from {LYRICS_SCHEMA}.genre_theme_year_count
    where topic_analysis_version = %(analysis_version)s
    group by year, main_theme
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={"analysis_version": TOPIC_ANALYSIS_VERSION},
        )

    def get_presence_year_counts(self):
        sql = f"""
    select ce.year, tt.topic, count(*)::int as entry_count
    from {LYRICS_SCHEMA}.chart_entry ce
    join {LYRICS_SCHEMA}.track_topic tt on tt.track_id = ce.track_id
    where tt.analysis_version = %(analysis_version)s
      and (tt.is_primary or tt.presence_probability >= %(presence_threshold)s)
    group by ce.year, tt.topic
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": TOPIC_ANALYSIS_VERSION,
                "presence_threshold": TOPIC_PRESENCE_THRESHOLD,
            },
        )


class VocabularyRepository:
    GENRE_SIZE_CTE = f"""genre_size as (
      select
        broad_genre,
        count(*) as track_count,
        sum(count(*)) over () as all_track_count
      from {LYRICS_SCHEMA}.genre_track
      group by broad_genre
    )"""

    def __init__(self, engine):
        self._engine = engine

    def get_distinctive_terms(self):
        sql = f"""
    with {self.GENRE_SIZE_CTE},
    term_track as (
      select gt.broad_genre, m.ngram as term, count(*) as track_count
      from {LYRICS_SCHEMA}.lyrics_ngram_metric m
      join {LYRICS_SCHEMA}.genre_track gt on gt.track_id = m.track_id
      where m.analysis_version = %(analysis_version)s
        and m.n <= %(max_ngram_length)s
        -- Checks each word of a phrase; MAX_NGRAM_LENGTH is 2, so two parts cover every phrase
        and split_part(m.ngram, ' ', 1) not in (select word from {LYRICS_SCHEMA}.strong_profanity_word)
        and split_part(m.ngram, ' ', 2) not in (select word from {LYRICS_SCHEMA}.strong_profanity_word)
      group by gt.broad_genre, m.ngram
      union all
      select gt.broad_genre, %(profanity_term)s, count(distinct lw.track_id)
      from {LYRICS_SCHEMA}.lyrics_word lw
      join {LYRICS_SCHEMA}.genre_track gt on gt.track_id = lw.track_id
      where lw.analysis_version = %(analysis_version)s
        and lw.is_explicit
      group by gt.broad_genre
    ),
    scored as (
      select
        tt.broad_genre,
        tt.term,
        tt.term = %(profanity_term)s as is_profanity,
        tt.track_count * %(percent)s::float / gs.track_count as genre_share,
        (sum(tt.track_count) over (partition by tt.term) - tt.track_count) * %(percent)s::float
          / (gs.all_track_count - gs.track_count) as other_share
      from term_track tt
      join genre_size gs on gs.broad_genre = tt.broad_genre
    ),
    ranked as (
      select
        *,
        genre_share / (other_share + %(smoothing)s) as lift,
        row_number() over (
          partition by broad_genre, is_profanity
          order by genre_share / (other_share + %(smoothing)s) desc
        ) as term_rank
      from scored
      where broad_genre = any(%(genres)s::text[])
        and genre_share >= %(min_share)s
    )
    select broad_genre, term as ngram, genre_share, other_share
    from ranked
    where (not is_profanity and term_rank <= %(term_count)s)
       or (is_profanity and genre_share > other_share)
    order by broad_genre, lift desc
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "max_ngram_length": MAX_NGRAM_LENGTH,
                "profanity_term": PROFANITY_TERM,
                "percent": PERCENT,
                "smoothing": DISTINCTIVE_SMOOTHING_POINTS,
                "genres": list(VOCABULARY_GENRES),
                "min_share": MIN_DISTINCTIVE_SHARE,
                "term_count": DISTINCTIVE_TERM_COUNT,
            },
        )

    def get_explicit_year_rates(self):
        sql = f"""
    with song as (
      select
        ce.year,
        ce.track_id,
        sum(lw.frequency) as word_count,
        coalesce(
          sum(lw.frequency) filter (where lw.is_explicit), 0
        ) as explicit_word_count
      from {LYRICS_SCHEMA}.lyrics_word lw
      join {LYRICS_SCHEMA}.chart_entry ce on ce.track_id = lw.track_id
      where lw.analysis_version = %(analysis_version)s
      group by ce.year, ce.track_id
    )
    select
      year,
      sum(explicit_word_count) * %(words_per_rate)s::float / sum(word_count) as explicit_rate,
      count(*) filter (where explicit_word_count > 0) * %(percent)s::float / count(*)
        as explicit_song_share
    from song
    group by year
    order by year
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "words_per_rate": WORDS_PER_RATE,
                "percent": PERCENT,
            },
        )

    def get_shared_top_words(self):
        sql = f"""
    with {self.GENRE_SIZE_CTE},
    word_share as (
      select gt.broad_genre, lw.word, count(*)::float / gs.track_count as genre_share
      from {LYRICS_SCHEMA}.lyrics_word lw
      join {LYRICS_SCHEMA}.genre_track gt on gt.track_id = lw.track_id
      join genre_size gs on gs.broad_genre = gt.broad_genre
      where lw.analysis_version = %(analysis_version)s
        and gt.broad_genre = any(%(genres)s::text[])
        and not lw.is_explicit
      group by gt.broad_genre, lw.word, gs.track_count
    ),
    ranked as (
      select
        *,
        row_number() over (partition by broad_genre order by genre_share desc) as word_rank
      from word_share
    )
    select word
    from ranked
    where word_rank <= %(word_rank)s
    group by word
    having count(*) = cardinality(%(genres)s::text[])
    order by avg(genre_share) desc
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "genres": list(VOCABULARY_GENRES),
                "word_rank": SHARED_WORD_RANK,
            },
        )["word"].tolist()


class EmotionRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_shares(self):
        sql = f"""
    with year_word as (
      select ce.year, lw.word, sum(lw.frequency) as frequency
      from {LYRICS_SCHEMA}.lyrics_word lw
      join {LYRICS_SCHEMA}.chart_entry ce on ce.track_id = lw.track_id
      where lw.analysis_version = %(analysis_version)s
        and not lw.is_explicit
      group by ce.year, lw.word
    ),
    year_total as (
      select year, sum(frequency) as frequency
      from year_word
      group by year
    )
    select
      yw.year,
      em.display_name as emotion,
      sum(yw.frequency)::int as word_count,
      yt.frequency::int as year_word_count,
      sum(yw.frequency) * %(percent)s::float / yt.frequency as word_share
    from year_word yw
    join {LYRICS_SCHEMA}.word_emotion we on we.word = yw.word
    join {LYRICS_SCHEMA}.emotion em on em.emotion_id = we.emotion_id
    join year_total yt on yt.year = yw.year
    group by yw.year, em.display_name, yt.frequency
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "percent": PERCENT,
            },
        )
