import pandas as pd
import pytest

from services.transformers import TrackMerger

TRACK_NAME = "Lemon"
ACCENTED_TRACK_NAME = "Lémon"
SUBTITLE = "All Night"
SUBTITLED_TRACK_NAME = f"{TRACK_NAME} {SUBTITLE}"
ARTIST_NAME = "N.E.R.D"
DUET_ARTIST_NAME = f"{ARTIST_NAME} & Rihanna"
FEATURED_ARTIST_NAME = f"{ARTIST_NAME} feat. Rihanna"
OTHER_ARTIST_NAME = "Kesha"
GROUP_CREDIT_ARTIST_NAME = f"{ARTIST_NAME}, Rihanna & Drake"
SIMILAR_ARTIST_NAME = f"{ARTIST_NAME} Junior"
CONJOINED_ARTIST_NAME = f"{ARTIST_NAME} and Rihanna"
ARTICLE_ARTIST_NAME = f"The {ARTIST_NAME}"
SPELLED_ARTIST_NAME = "ASAP Rocky"
DOLLAR_ARTIST_NAME = SPELLED_ARTIST_NAME.replace("S", "$")
SEPARATOR_WORD_ARTIST_NAME = "X Ambassadors"
BILLBOARD_ALIAS, CANDIDATE_ALIAS = next(
    iter(TrackMerger.BILLBOARD_ARTIST_ALIASES.items())
)
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


def candidate_track(
    track_name=TRACK_NAME,
    genre=EXPECTED_GENRE,
    year=RELEASE_YEAR,
    popularity=POPULARITY,
    artist_name=ARTIST_NAME,
):
    return {
        TrackMerger.TRACK_NAME_COLUMN: track_name,
        TrackMerger.ARTIST_NAME_COLUMN: artist_name,
        TrackMerger.CANDIDATE_YEAR_COLUMN: year,
        TrackMerger.CANDIDATE_POPULARITY_COLUMN: popularity,
        GENRE_COLUMN: genre,
    }


def candidate_df(*tracks):
    return pd.DataFrame(tracks)


def billboard_df(track_name=TRACK_NAME, artist_name=ARTIST_NAME):
    return pd.DataFrame(
        {
            TrackMerger.TRACK_NAME_COLUMN: [track_name],
            TrackMerger.ARTIST_NAME_COLUMN: [artist_name],
        }
    )


def merged_genre(merger, billboard_track_df, *candidate_tracks):
    track_df = merger.transform(billboard_track_df, candidate_df(*candidate_tracks))
    return track_df[GENRE_COLUMN].iloc[0]


def matched_genre(merger, *candidate_tracks):
    return merged_genre(merger, billboard_df(), *candidate_tracks)


class TestBestMatchTieBreaking:
    def test_prefers_the_original_over_an_edit_from_the_same_year(self, merger):
        edit = candidate_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)

        assert matched_genre(merger, edit, candidate_track()) == EXPECTED_GENRE

    def test_treats_a_featured_credit_as_the_original(self, merger):
        edit = candidate_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)
        featured = candidate_track(f"{TRACK_NAME} (feat. Rihanna)")

        assert matched_genre(merger, edit, featured) == EXPECTED_GENRE

    def test_treats_a_with_credit_as_the_original(self, merger):
        edit = candidate_track(f"{TRACK_NAME} - Radio Edit", OTHER_GENRE)
        featured = candidate_track(f"{TRACK_NAME} (with Rihanna)")

        assert matched_genre(merger, edit, featured) == EXPECTED_GENRE

    def test_prefers_the_more_popular_of_equally_named_versions(self, merger):
        less_popular = candidate_track(genre=OTHER_GENRE)
        more_popular = candidate_track(popularity=HIGHER_POPULARITY)

        assert matched_genre(merger, less_popular, more_popular) == EXPECTED_GENRE

    def test_still_prefers_an_earlier_edit_over_a_later_original(self, merger):
        later_original = candidate_track(genre=OTHER_GENRE, year=LATER_RELEASE_YEAR)
        earlier_edit = candidate_track(f"{TRACK_NAME} - Radio Edit")

        assert matched_genre(merger, later_original, earlier_edit) == EXPECTED_GENRE

    def test_prefers_an_exact_artist_match_over_a_lead_artist_match(self, merger):
        lead_artist = candidate_track(genre=OTHER_GENRE)
        exact_artist = candidate_track(artist_name=DUET_ARTIST_NAME)

        assert (
            merged_genre(
                merger,
                billboard_df(artist_name=DUET_ARTIST_NAME),
                lead_artist,
                exact_artist,
            )
            == EXPECTED_GENRE
        )


class TestTrackMatching:
    def test_matches_titles_regardless_of_case_and_punctuation(self, merger):
        chart_df = billboard_df(track_name=f"{TRACK_NAME.upper()}!")

        assert merged_genre(merger, chart_df, candidate_track()) == EXPECTED_GENRE

    def test_matches_titles_regardless_of_accents(self, merger):
        accented = candidate_track(ACCENTED_TRACK_NAME)

        assert matched_genre(merger, accented) == EXPECTED_GENRE

    def test_ignores_featured_credits_in_billboard_titles(self, merger):
        chart_df = billboard_df(track_name=f"{TRACK_NAME} (feat. Rihanna)")

        assert merged_genre(merger, chart_df, candidate_track()) == EXPECTED_GENRE

    def test_skips_alternate_versions(self, merger):
        live = candidate_track(f"{TRACK_NAME} - Live")

        assert pd.isna(matched_genre(merger, live))

    def test_matches_an_alternate_version_that_charted(self, merger):
        remix_name = f"{TRACK_NAME} (Remix)"
        chart_df = billboard_df(track_name=remix_name)

        assert merged_genre(merger, chart_df, candidate_track(remix_name)) == (
            EXPECTED_GENRE
        )

    def test_matches_a_subtitle_followed_by_a_version_tag(self, merger):
        chart_df = billboard_df(track_name=SUBTITLED_TRACK_NAME)
        tagged = candidate_track(f"{TRACK_NAME} ({SUBTITLE}) [Radio Version]")

        assert merged_genre(merger, chart_df, tagged) == EXPECTED_GENRE

    def test_skips_a_subtitled_alternate_version(self, merger):
        chart_df = billboard_df(track_name=SUBTITLED_TRACK_NAME)
        live = candidate_track(f"{TRACK_NAME} ({SUBTITLE}) [Live]")

        assert pd.isna(merged_genre(merger, chart_df, live))

    def test_keeps_the_billboard_track_name(self, merger):
        billboard_track_name = f"{TRACK_NAME.upper()}!"
        track_df = merger.transform(
            billboard_df(track_name=billboard_track_name),
            candidate_df(candidate_track()),
        )

        assert track_df[TrackMerger.TRACK_NAME_COLUMN].tolist() == [
            billboard_track_name
        ]


class TestArtistMatching:
    def test_matches_a_featured_billboard_credit_to_the_primary_artist(
        self, merger
    ):
        chart_df = billboard_df(artist_name=FEATURED_ARTIST_NAME)

        assert merged_genre(merger, chart_df, candidate_track()) == EXPECTED_GENRE

    def test_matches_a_billboard_duet_to_its_lead_artist(self, merger):
        chart_df = billboard_df(artist_name=DUET_ARTIST_NAME)

        assert merged_genre(merger, chart_df, candidate_track()) == EXPECTED_GENRE

    def test_matches_billboard_aliases_to_candidate_names(self, merger):
        chart_df = billboard_df(artist_name=BILLBOARD_ALIAS)
        aliased = candidate_track(artist_name=CANDIDATE_ALIAS)

        assert merged_genre(merger, chart_df, aliased) == EXPECTED_GENRE

    def test_leaves_songs_by_another_artist_unmatched(self, merger):
        other_artist = candidate_track(artist_name=OTHER_ARTIST_NAME)

        assert pd.isna(matched_genre(merger, other_artist))


    def test_matches_the_lead_artist_of_a_longer_candidate_credit(self, merger):
        group_credit = candidate_track(artist_name=GROUP_CREDIT_ARTIST_NAME)

        assert matched_genre(merger, group_credit) == EXPECTED_GENRE

    def test_leaves_an_artist_sharing_only_the_first_words_unmatched(self, merger):
        similar_artist = candidate_track(artist_name=SIMILAR_ARTIST_NAME)

        assert pd.isna(matched_genre(merger, similar_artist))

    def test_matches_and_written_as_an_ampersand(self, merger):
        chart_df = billboard_df(artist_name=CONJOINED_ARTIST_NAME)
        duet = candidate_track(artist_name=DUET_ARTIST_NAME)

        assert merged_genre(merger, chart_df, duet) == EXPECTED_GENRE

    def test_ignores_a_leading_the(self, merger):
        with_article = candidate_track(artist_name=ARTICLE_ARTIST_NAME)

        assert matched_genre(merger, with_article) == EXPECTED_GENRE

    def test_matches_a_dollar_sign_spelled_as_an_s(self, merger):
        chart_df = billboard_df(artist_name=SPELLED_ARTIST_NAME)
        stylized = candidate_track(artist_name=DOLLAR_ARTIST_NAME)

        assert merged_genre(merger, chart_df, stylized) == EXPECTED_GENRE

    def test_matches_an_artist_name_starting_with_a_separator_word(self, merger):
        chart_df = billboard_df(artist_name=SEPARATOR_WORD_ARTIST_NAME)
        same_artist = candidate_track(artist_name=SEPARATOR_WORD_ARTIST_NAME)

        assert merged_genre(merger, chart_df, same_artist) == EXPECTED_GENRE
