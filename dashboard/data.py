import pandas as pd

LYRICS_SCHEMA = "billboard_lyrics"
TOPIC_ANALYSIS_VERSION = "v1"
TOPIC_PRESENCE_THRESHOLD = 0.7


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
    select ch.year, tp.display_name as topic, count(*)::int as entry_count
    from {LYRICS_SCHEMA}.chart_track ct
    join {LYRICS_SCHEMA}.chart ch on ch.chart_id = ct.chart_id
    join {LYRICS_SCHEMA}.lyrics_topic lt on lt.track_id = ct.track_id
    join {LYRICS_SCHEMA}.topic tp on tp.topic_id = lt.topic_id
    where lt.analysis_version = %(analysis_version)s
      and (lt.is_primary or lt.presence_probability >= %(presence_threshold)s)
    group by ch.year, tp.display_name
    """
        return pd.read_sql(
            sql,
            self._engine,
            params={
                "analysis_version": TOPIC_ANALYSIS_VERSION,
                "presence_threshold": TOPIC_PRESENCE_THRESHOLD,
            },
        )
