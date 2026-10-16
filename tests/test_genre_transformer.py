import pandas as pd
import pytest

from transformers import GenreTransformer

GENRE_COLUMN = "genre"
NAME_COLUMN = "name"
GENRE = "hip-hop"
OTHER_GENRE = "dance"


@pytest.fixture
def transformer():
    return GenreTransformer()


def genre_names(transformer, *genres):
    track_df = pd.DataFrame({GENRE_COLUMN: genres})
    return transformer.transform(track_df)[NAME_COLUMN].tolist()


class TestTransform:
    def test_builds_one_genre_per_distinct_genre(self, transformer):
        assert genre_names(transformer, GENRE, OTHER_GENRE, GENRE) == [
            GENRE,
            OTHER_GENRE,
        ]

    def test_normalizes_genre_names(self, transformer):
        assert genre_names(transformer, f"  {GENRE.upper()} ") == [GENRE]

    def test_merges_genres_that_differ_only_in_formatting(self, transformer):
        assert genre_names(transformer, GENRE, GENRE.title()) == [GENRE]

    def test_skips_tracks_without_a_genre(self, transformer):
        assert genre_names(transformer, GENRE, None) == [GENRE]
