import pandas as pd
import pytest

from transformers import TrackMerger

TRACK_NAME = "Lemon"
ARTIST_NAME = "N.E.R.D"
GENRE_COLUMN = "genre"
EXPECTED_GENRE = "hip-hop"
OTHER_GENRE = "dance"
RELEASE_YEAR = 2017
LATER_RELEASE_YEAR = RELEASE_YEAR + 1
POPULARITY = 50
HIGHER_POPULARITY = POPULARITY + 1


@pytest.fixture
def merger():
    return TrackMerger()


def spotify_track(
    track_name=TRACK_NAME,
    genre=EXPECTED_GENRE,
    year=RELEASE_YEAR,
    popularity=POPULARITY,
):
    return {
        TrackMerger.TRACK_NAME_COLUMN: track_name,
        TrackMerger.ARTIST_NAME_COLUMN: ARTIST_NAME,
        TrackMerger.SPOTIFY_YEAR_COLUMN: year,
        TrackMerger.SPOTIFY_POPULARITY_COLUMN: popularity,
        GENRE_COLUMN: genre,
    }


def spotify_df(*tracks):
    return (
        pd.DataFrame(tracks)
        .rename_axis(TrackMerger.SPOTIFY_TRACK_ID_COLUMN)
        .reset_index()
        .reset_index(names=TrackMerger.SPOTIFY_INDEX_COLUMN)
    )


def billboard_df():
    return pd.DataFrame(
        {
            TrackMerger.TRACK_NAME_COLUMN: [TRACK_NAME],
            TrackMerger.ARTIST_NAME_COLUMN: [ARTIST_NAME],
        }
    )


def matched_genre(merger, *spotify_tracks):
    track_df = merger.transform(billboard_df(), spotify_df(*spotify_tracks))
    return track_df[GENRE_COLUMN].iloc[0]


class TestBestMatchTieBreaking:
    def test_prefers_the_original_over_an_edit_from_the_same_year(self, merger):
        edit = spotify_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)

        assert matched_genre(merger, edit, spotify_track()) == EXPECTED_GENRE

    def test_treats_a_featured_credit_as_the_original(self, merger):
        edit = spotify_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)
        featured = spotify_track(f"{TRACK_NAME} (feat. Rihanna)")

        assert matched_genre(merger, edit, featured) == EXPECTED_GENRE

    def test_treats_a_with_credit_as_the_original(self, merger):
        edit = spotify_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)
        featured = spotify_track(f"{TRACK_NAME} (with Rihanna)")

        assert matched_genre(merger, edit, featured) == EXPECTED_GENRE

    def test_prefers_the_more_popular_of_equally_named_versions(self, merger):
        less_popular = spotify_track(genre=OTHER_GENRE)
        more_popular = spotify_track(popularity=HIGHER_POPULARITY)

        assert matched_genre(merger, less_popular, more_popular) == EXPECTED_GENRE

    def test_still_prefers_an_earlier_edit_over_a_later_original(self, merger):
        later_original = spotify_track(genre=OTHER_GENRE, year=LATER_RELEASE_YEAR)
        earlier_edit = spotify_track(f"{TRACK_NAME} - Radio Edit")

        assert matched_genre(merger, later_original, earlier_edit) == EXPECTED_GENRE
