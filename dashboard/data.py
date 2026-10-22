import pandas as pd

LYRICS_SCHEMA = "billboard_lyrics"
TOPIC_ANALYSIS_VERSION = "v1"
TOPIC_PRESENCE_THRESHOLD = 0.7
LYRICS_ANALYSIS_VERSION = "v3"
PERCENT = 100
WORDS_PER_RATE = 1000
MS_PER_MINUTE = 60000
# Spotify audio features cover under 60% of chart entries after this year
SOUND_LAST_YEAR = 2022
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
# Words used in fewer chart entries than this across all years are too rare to track over time
MIN_WORD_ENTRY_COUNT = 100


class GenreRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_counts(self):
        sql = f"""
          select 
            year, 
            broad_genre, 
            count(*) as entry_count
          from {LYRICS_SCHEMA}.chart_entry
          where broad_genre is not null
          group by year, broad_genre
        """
        return pd.read_sql(sql, self._engine)

    def get_topic_shares(self):
        sql = f"""
          with genre_topic as (
            select 
              broad_genre, 
              main_theme as main_topic, 
              sum(entry_count) as entry_count
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
          select 
            year, 
            main_theme as main_topic, 
            sum(entry_count)::int as entry_count
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
          select 
            ce.year, 
            tt.topic, 
            count(*) as entry_count
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
    GENRE_SIZE_CTE = f"""
      genre_size as (
        select
          broad_genre,
          count(*) as track_count,
          sum(count(*)) over () as all_track_count
        from {LYRICS_SCHEMA}.genre_track
        group by broad_genre
    )"""
    GENRE_TRACK_SQL = f"""
      select 
        track_id, 
        broad_genre as category
      from {LYRICS_SCHEMA}.genre_track
    """
    TOPIC_TRACK_SQL = f"""
      select 
        track_id, 
        topic as category
      from {LYRICS_SCHEMA}.track_topic
      where is_primary and analysis_version = %(topic_analysis_version)s
    """

    DISTINCTIVE_TERMS_SQL = f"""
      with category_track as (
        {{category_track_sql}}
      ),
      category_size as (
        select
          category,
          count(*) as track_count,
          sum(count(*)) over () as all_track_count
        from category_track
        group by category
      ),
      term_track as (
        select 
          ct.category, 
          m.ngram as term, 
          count(*) as track_count
        from {LYRICS_SCHEMA}.lyrics_ngram_metric m
        join category_track ct on ct.track_id = m.track_id
        where m.analysis_version = %(analysis_version)s
          and m.n <= %(max_ngram_length)s
          -- Checks each word of a phrase; MAX_NGRAM_LENGTH is 2, so two parts cover every phrase
          and split_part(m.ngram, ' ', 1) not in (select word from {LYRICS_SCHEMA}.strong_profanity_word)
          and split_part(m.ngram, ' ', 2) not in (select word from {LYRICS_SCHEMA}.strong_profanity_word)
        group by ct.category, m.ngram
        union all
        select ct.category, %(profanity_term)s, count(*)
        from {LYRICS_SCHEMA}.track_explicit te
        join category_track ct on ct.track_id = te.track_id
        where te.analysis_version = %(analysis_version)s
          and te.has_explicit
        group by ct.category
      ),
      scored as (
        select
          tt.category,
          tt.term,
          tt.term = %(profanity_term)s as is_profanity,
          tt.track_count * %(percent)s::float / cs.track_count as category_share,
          (sum(tt.track_count) over (partition by tt.term) - tt.track_count) * %(percent)s::float
            / (cs.all_track_count - cs.track_count) as other_share
        from term_track tt
        join category_size cs on cs.category = tt.category
      ),
      ranked as (
        select
          *,
          category_share / (other_share + %(smoothing)s) as lift,
          row_number() over (
            partition by category, is_profanity
            order by category_share / (other_share + %(smoothing)s) desc
          ) as term_rank
        from scored
        where category = any(%(categories)s::text[])
          and category_share >= %(min_share)s
      )
      select category, term as ngram, category_share, other_share
      from ranked
      where (not is_profanity and term_rank <= %(term_count)s)
        or (is_profanity and category_share > other_share)
      order by category, lift desc
    """
    WORD_YEAR_COUNTS_SQL = f"""
    with topic_entry as (
      select ce.*, tt.topic as main_topic
      from {LYRICS_SCHEMA}.chart_entry ce
      left join {LYRICS_SCHEMA}.track_topic tt
        on tt.track_id = ce.track_id
        and tt.is_primary
        and tt.analysis_version = %(topic_analysis_version)s
    ),
    word_entry as (
      select
        ce.year,
        ce.broad_genre,
        ce.main_topic,
        ce.chart_track_id,
        case when lw.is_explicit then %(profanity_term)s else lw.word end as word
      from topic_entry ce
      join {LYRICS_SCHEMA}.lyrics_word lw on lw.track_id = ce.track_id
      where lw.analysis_version = %(analysis_version)s
    ),
    year_word as (
      select year, broad_genre, main_topic, word, count(distinct chart_track_id) as entry_count
      from word_entry
      group by year, broad_genre, main_topic, word
    ),
    common_word as (
      select word
      from year_word
      group by word
      having sum(entry_count) >= %(min_entry_count)s
    ),
    year_size as (
      select year, broad_genre, main_topic, count(*) as entry_count
      from topic_entry
      group by year, broad_genre, main_topic
    )
    select
      yw.year,
      yw.broad_genre,
      yw.main_topic,
      yw.word,
      yw.entry_count,
      ys.entry_count as year_entry_count
    from year_word yw
    join common_word cw on cw.word = yw.word
    join year_size ys
      on ys.year = yw.year
      and ys.broad_genre is not distinct from yw.broad_genre
      and ys.main_topic is not distinct from yw.main_topic
    """
    SHARED_TOP_WORDS_SQL = f"""
    with {GENRE_SIZE_CTE},
    word_share as (
      select 
        gt.broad_genre, 
        lw.word, count(*)::float / gs.track_count as genre_share
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
    select 
      word
    from ranked
    where word_rank <= %(word_rank)s
    group by word
    having count(*) = cardinality(%(genres)s::text[])
    order by avg(genre_share) desc
    """

    def __init__(self, engine):
        self._engine = engine

    def get_genre_distinctive_terms(self):
        return self._get_distinctive_terms(
            self.GENRE_TRACK_SQL,
            VOCABULARY_GENRES,
        )

    def get_topic_distinctive_terms(self, topics):
        return self._get_distinctive_terms(
            self.TOPIC_TRACK_SQL,
            topics,
        )

    def _get_distinctive_terms(self, category_track_sql, categories):
        sql = self.DISTINCTIVE_TERMS_SQL.format(category_track_sql=category_track_sql)
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "topic_analysis_version": TOPIC_ANALYSIS_VERSION,
                "max_ngram_length": MAX_NGRAM_LENGTH,
                "profanity_term": PROFANITY_TERM,
                "percent": PERCENT,
                "smoothing": DISTINCTIVE_SMOOTHING_POINTS,
                "categories": list(categories),
                "min_share": MIN_DISTINCTIVE_SHARE,
                "term_count": DISTINCTIVE_TERM_COUNT,
            },
        )

    def get_word_year_counts(self):
        return pd.read_sql(
            self.WORD_YEAR_COUNTS_SQL,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "topic_analysis_version": TOPIC_ANALYSIS_VERSION,
                "profanity_term": PROFANITY_TERM,
                "min_entry_count": MIN_WORD_ENTRY_COUNT,
            },
        )

    def get_shared_top_words(self):
        return pd.read_sql(
            self.SHARED_TOP_WORDS_SQL,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "genres": list(VOCABULARY_GENRES),
                "word_rank": SHARED_WORD_RANK,
            },
        )["word"].tolist()


class ExplicitRepository:
    YEAR_RATES_SQL = f"""
      select
        ce.year,
        sum(te.explicit_word_count) * %(words_per_rate)s::float / sum(te.word_count)
          as explicit_rate,
        count(*) filter (where te.has_explicit) * %(percent)s::float / count(*)
          as explicit_song_share
      from {LYRICS_SCHEMA}.chart_entry ce
      join {LYRICS_SCHEMA}.track_explicit te on te.track_id = ce.track_id
      where te.analysis_version = %(analysis_version)s
      group by ce.year
      order by ce.year
    """
    BREAKDOWN_COUNTS_SQL = f"""
      select
        ce.year,
        ce.broad_genre,
        tt.topic as main_topic,
        count(*) filter (where te.has_explicit) as explicit_entry_count,
        count(*) as entry_count
      from {LYRICS_SCHEMA}.chart_entry ce
      join {LYRICS_SCHEMA}.track_explicit te on te.track_id = ce.track_id
      join {LYRICS_SCHEMA}.track_topic tt on tt.track_id = ce.track_id
      where te.analysis_version = %(lyrics_analysis_version)s
        and tt.is_primary
        and tt.analysis_version = %(topic_analysis_version)s
      group by ce.year, ce.broad_genre, tt.topic
    """

    def __init__(self, engine):
        self._engine = engine

    def get_year_rates(self):
        return pd.read_sql(
            self.YEAR_RATES_SQL,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "words_per_rate": WORDS_PER_RATE,
                "percent": PERCENT,
            },
        )

    def get_breakdown_counts(self):
        return pd.read_sql(
            self.BREAKDOWN_COUNTS_SQL,
            self._engine,
            params={
                "lyrics_analysis_version": LYRICS_ANALYSIS_VERSION,
                "topic_analysis_version": TOPIC_ANALYSIS_VERSION,
            },
        )


class EmotionRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_shares(self):
        sql = f"""
          with year_word as (
            select 
              ce.year, 
              lw.word, 
              sum(lw.frequency) as frequency
            from {LYRICS_SCHEMA}.lyrics_word lw
            join {LYRICS_SCHEMA}.chart_entry ce on ce.track_id = lw.track_id
            where lw.analysis_version = %(analysis_version)s
              and not lw.is_explicit
            group by ce.year, lw.word
          ),
          year_total as (
            select 
              year, 
              sum(frequency) as frequency
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

    def get_genre_shares(self):
        sql = f"""
          with genre_word as (
            select
              ce.broad_genre,
              lw.word,
              sum(lw.frequency) as frequency
            from {LYRICS_SCHEMA}.lyrics_word lw
            join {LYRICS_SCHEMA}.chart_entry ce on ce.track_id = lw.track_id
            where lw.analysis_version = %(analysis_version)s
              and not lw.is_explicit
              and ce.broad_genre is not null
            group by ce.broad_genre, lw.word
          ),
          genre_total as (
            select
              broad_genre,
              sum(frequency) as frequency,
              sum(sum(frequency)) over () as all_frequency
            from genre_word
            group by broad_genre
          ),
          genre_emotion as (
            select
              gw.broad_genre,
              em.display_name as emotion,
              sum(gw.frequency) as frequency
            from genre_word gw
            join {LYRICS_SCHEMA}.word_emotion we on we.word = gw.word
            join {LYRICS_SCHEMA}.emotion em on em.emotion_id = we.emotion_id
            group by gw.broad_genre, em.display_name
          )
          select
            ge.broad_genre,
            ge.emotion,
            gt.frequency::int as genre_word_count,
            ge.frequency * %(percent)s::float / gt.frequency as genre_share,
            sum(ge.frequency) over (partition by ge.emotion) * %(percent)s::float
              / gt.all_frequency as average_share
          from genre_emotion ge
          join genre_total gt on gt.broad_genre = ge.broad_genre
        """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": LYRICS_ANALYSIS_VERSION,
                "percent": PERCENT,
            },
        )


class EconomyRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_averages(self):
        sql = f"""
          select
            ei.display_name as indicator,
            extract(year from eo.observation_date)::int as year,
            avg(eo.value)::float as value
          from {LYRICS_SCHEMA}.economic_observation eo
          join {LYRICS_SCHEMA}.economic_indicator ei
            on ei.economic_indicator_id = eo.economic_indicator_id
          group by ei.display_name, extract(year from eo.observation_date)
        """
        return pd.read_sql(sql, self._engine)


class SoundRepository:
    def __init__(self, engine):
        self._engine = engine

    def get_year_averages(self):
        sql = f"""
          select
            ce.year,
            count(t.duration_ms) * %(percent)s::float / count(*) as matched_share,
            avg(t.duration_ms) / %(ms_per_minute)s::float as minutes,
            avg(t.valence)::float as valence,
            avg(t.energy)::float as energy,
            avg(t.danceability)::float as danceability,
            avg(t.acousticness)::float as acousticness,
            avg(t.speechiness)::float as speechiness
          from {LYRICS_SCHEMA}.chart_entry ce
          join {LYRICS_SCHEMA}.track t on t.track_id = ce.track_id
          where ce.year <= %(last_year)s
          group by ce.year
          order by ce.year
        """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "percent": PERCENT,
                "ms_per_minute": MS_PER_MINUTE,
                "last_year": SOUND_LAST_YEAR,
            },
        )
