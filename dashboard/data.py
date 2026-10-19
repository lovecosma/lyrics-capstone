import pandas as pd

LYRICS_SCHEMA = "billboard_lyrics"


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
