import pytest
from lyrics_helpers import song

from lyrics_analysis import LyricsCleaner

LINE_BEFORE = "I walked into the room"
LINE_AFTER = "and the lights went down"


@pytest.fixture
def cleaner():
    return LyricsCleaner()


def lyric_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


class TestScrapeArtifacts:
    def test_removes_contributors_header_at_the_start(self, cleaner):
        lyrics = song("42 ContributorsSong Title Lyrics", LINE_BEFORE)

        assert lyric_lines(cleaner.clean(lyrics)) == [LINE_BEFORE]

    def test_removes_you_might_also_like_and_splits_the_lines_it_joined(self, cleaner):
        lyrics = f"{LINE_BEFORE}You might also like{LINE_AFTER}"

        assert lyric_lines(cleaner.clean(lyrics)) == [LINE_BEFORE, LINE_AFTER]

    def test_removes_ticket_ads(self, cleaner):
        lyrics = f"{LINE_BEFORE}See Adele LiveGet tickets as low as $45{LINE_AFTER}"

        assert lyric_lines(cleaner.clean(lyrics)) == [LINE_BEFORE, LINE_AFTER]

    def test_removes_embed_at_the_end(self, cleaner):
        lyrics = f"{LINE_BEFORE}Embed"

        assert lyric_lines(cleaner.clean(lyrics)) == [LINE_BEFORE]

    def test_keeps_the_word_embed_inside_lyrics(self, cleaner):
        lyrics = song("I'll embed it in your brain", LINE_AFTER)

        assert cleaner.clean(lyrics) == lyrics


class TestSectionHeaders:
    @pytest.mark.parametrize(
        "header",
        [
            "Verse 1:",
            "Chorus",
            "CHORUS:",
            "Pre-Chorus",
            "  Bridge  ",
            "Outro",
            "{Chorus}",
            "{Verse 2}",
            "(chorus)",
            "(Chorus 16X)",
            "(Chorus: Usher)",
            "[Hook - 112 (Q)",
            "-CHORUS-",
            "Chorus x2",
            "Chorus until end",
        ],
    )
    def test_removes_header_lines(self, cleaner, header):
        lyrics = song(LINE_BEFORE, header, LINE_AFTER)

        assert lyric_lines(cleaner.clean(lyrics)) == [LINE_BEFORE, LINE_AFTER]

    @pytest.mark.parametrize(
        "lyric",
        [
            "All the boys say:",
            "Take it to the chorus",
            "Let's cross the bridge",
            "Bridge over troubled water",
            "Hook, line and sinker",
            "(Hook me up, baby)",
            "Chorus girl",
            "Verse 1: I walked in",
        ],
    )
    def test_keeps_lyrics_that_only_mention_a_section_word(self, cleaner, lyric):
        lyrics = song(LINE_BEFORE, lyric, LINE_AFTER)

        assert cleaner.clean(lyrics) == lyrics


def test_leaves_clean_lyrics_unchanged(cleaner):
    lyrics = song(LINE_BEFORE, LINE_AFTER)

    assert cleaner.clean(lyrics) == lyrics
