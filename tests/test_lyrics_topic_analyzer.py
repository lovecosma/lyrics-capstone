from http import HTTPStatus

import httpx2
import pandas as pd
import pytest
from lyrics_helpers import song
from typesafe_sdk import (
    ChoiceAnswer,
    NoulAnswer,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPITimeoutError,
    TypeSafeRateLimitError,
)

from services.lyrics_analysis import LyricsCleaner, LyricsTopicAnalyzer

PRIMARY_TOPIC_QUESTION = LyricsTopicAnalyzer.PRIMARY_TOPIC_QUESTION_ID
OTHER_TOPIC = LyricsTopicAnalyzer.OTHER_TOPIC
THEME = "love_relationships"
CHOSEN_THEME = "party_celebration"
TOPIC_IDS = {THEME: 11, CHOSEN_THEME: 12, OTHER_TOPIC: 13}
TOPIC_DESCRIPTIONS = {
    THEME: "Romantic love or being in a relationship",
    CHOSEN_THEME: "Partying, dancing, or having a good time",
    OTHER_TOPIC: "None of the themes above is central to the song",
}
CHOSEN_THEME_PROBABILITY = 0.7
PRESENCE_PROBABILITY = 0.4
MODEL = "jev-test"
REQUEST_TIMEOUT_SECONDS = 30.0
OLDER_ANALYSIS_VERSION = "v0"

GOOD_TRACK = {
    "track_id": 1,
    "title": "Neon Nights",
    "artist_name": "The Example Band",
    "lyrics": song("We dance until the morning", "Chorus:", "The city never sleeps"),
}
FAILING_TRACK = {
    "track_id": 2,
    "title": "Broken Signal",
    "artist_name": "The Test Pilots",
    "lyrics": song("Static on the radio"),
}
TRACK_IDS = (GOOD_TRACK["track_id"], FAILING_TRACK["track_id"])


def topic_response(questions, without_probability_for=None, without_presence_for=None):
    topics = list(questions[PRIMARY_TOPIC_QUESTION].criteria)
    other_probability = (1 - CHOSEN_THEME_PROBABILITY) / (len(topics) - 1)
    probabilities = {
        topic: CHOSEN_THEME_PROBABILITY if topic == CHOSEN_THEME else other_probability
        for topic in topics
        if topic != without_probability_for
    }
    presence_answers = {
        question: NoulAnswer(type="noul", noul=PRESENCE_PROBABILITY)
        for question in questions
        if question not in (PRIMARY_TOPIC_QUESTION, without_presence_for)
    }
    primary_answer = ChoiceAnswer(
        type="choice",
        choice=CHOSEN_THEME,
        confidence=CHOSEN_THEME_PROBABILITY,
        probabilities=probabilities,
    )
    return SystemOneResponse.model_construct(
        model=MODEL,
        answers={PRIMARY_TOPIC_QUESTION: primary_answer, **presence_answers},
    )


class FakeTypeSafeClient:
    def __init__(self, reply_for_failing_track=None):
        self.reply_for_failing_track = reply_for_failing_track
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc_info):
        return False

    async def system_one(self, state, questions):
        self.requests.append((state, questions))
        if (
            state["song"]["title"] == FAILING_TRACK["title"]
            and self.reply_for_failing_track
        ):
            return self.reply_for_failing_track(questions)
        return topic_response(questions)


def raising(error):
    def reply(_questions):
        raise error

    return reply


@pytest.fixture
def topic_df():
    return pd.DataFrame(
        {
            LyricsTopicAnalyzer.TOPIC_ID_COLUMN: list(TOPIC_IDS.values()),
            LyricsTopicAnalyzer.TOPIC_NAME_COLUMN: list(TOPIC_IDS),
            LyricsTopicAnalyzer.TOPIC_DESCRIPTION_COLUMN: [
                TOPIC_DESCRIPTIONS[topic] for topic in TOPIC_IDS
            ],
        }
    )


@pytest.fixture
def client():
    return FakeTypeSafeClient()


def analyze(topic_df, client, *tracks):
    analyzer = LyricsTopicAnalyzer(topic_df, lambda: client)
    return analyzer.analyze(pd.DataFrame(tracks or [GOOD_TRACK]))


def value_for(lyrics_topic_df, topic, column):
    rows_by_topic_id = lyrics_topic_df.set_index(LyricsTopicAnalyzer.TOPIC_ID_COLUMN)
    return rows_by_topic_id.at[TOPIC_IDS[topic], column]


def sent_questions(client):
    _, questions = client.requests[0]
    return questions


def sent_song(client):
    state, _ = client.requests[0]
    return state["song"]


class TestQuestions:
    def test_asks_for_the_main_theme_across_every_topic(self, topic_df, client):
        analyze(topic_df, client)

        assert set(sent_questions(client)[PRIMARY_TOPIC_QUESTION].criteria) == set(
            TOPIC_IDS
        )

    def test_asks_whether_each_theme_is_present_except_other(self, topic_df, client):
        analyze(topic_df, client)

        assert set(sent_questions(client)) - {PRIMARY_TOPIC_QUESTION} == set(
            TOPIC_IDS
        ) - {OTHER_TOPIC}


class TestSongSentToTypeSafe:
    def test_sends_the_title(self, topic_df, client):
        analyze(topic_df, client)

        assert sent_song(client)["title"] == GOOD_TRACK["title"]

    def test_sends_the_artist(self, topic_df, client):
        analyze(topic_df, client)

        assert sent_song(client)["artist"] == GOOD_TRACK["artist_name"]

    def test_sends_cleaned_lyrics(self, topic_df, client):
        analyze(topic_df, client)

        assert sent_song(client)["lyrics"] == LyricsCleaner().clean(
            GOOD_TRACK["lyrics"]
        )


class TestTopicRows:
    def test_returns_one_row_per_topic(self, topic_df, client):
        assert len(analyze(topic_df, client)) == len(TOPIC_IDS)

    def test_returns_columns_in_table_order(self, topic_df, client):
        assert analyze(topic_df, client).columns.tolist() == list(
            LyricsTopicAnalyzer.LYRICS_TOPIC_COLUMNS
        )

    def test_marks_only_the_chosen_theme_as_primary(self, topic_df, client):
        lyrics_topic_df = analyze(topic_df, client)
        primary_topic_ids = lyrics_topic_df.loc[
            lyrics_topic_df.is_primary, LyricsTopicAnalyzer.TOPIC_ID_COLUMN
        ]

        assert primary_topic_ids.tolist() == [TOPIC_IDS[CHOSEN_THEME]]

    def test_records_the_main_theme_probability(self, topic_df, client):
        primary_probability = value_for(
            analyze(topic_df, client),
            CHOSEN_THEME,
            LyricsTopicAnalyzer.PRIMARY_PROBABILITY_COLUMN,
        )

        assert primary_probability == CHOSEN_THEME_PROBABILITY

    def test_records_whether_a_theme_is_present(self, topic_df, client):
        presence_probability = value_for(
            analyze(topic_df, client),
            THEME,
            LyricsTopicAnalyzer.PRESENCE_PROBABILITY_COLUMN,
        )

        assert presence_probability == PRESENCE_PROBABILITY

    def test_leaves_presence_empty_for_other(self, topic_df, client):
        presence_probability = value_for(
            analyze(topic_df, client),
            OTHER_TOPIC,
            LyricsTopicAnalyzer.PRESENCE_PROBABILITY_COLUMN,
        )

        assert pd.isna(presence_probability)

    def test_records_the_model_version(self, topic_df, client):
        assert analyze(topic_df, client).model_version.eq(MODEL).all()

    def test_tags_rows_with_the_analysis_version(self, topic_df, client):
        assert (
            analyze(topic_df, client)
            .analysis_version.eq(LyricsTopicAnalyzer.ANALYSIS_VERSION)
            .all()
        )


class TestFailures:
    @pytest.mark.parametrize(
        "reply_for_failing_track",
        [
            pytest.param(
                raising(TypeSafeAPITimeoutError(REQUEST_TIMEOUT_SECONDS)), id="timeout"
            ),
            pytest.param(
                raising(TypeSafeAPIConnectionError("connection refused")),
                id="connection error",
            ),
            pytest.param(
                raising(
                    TypeSafeRateLimitError(
                        HTTPStatus.TOO_MANY_REQUESTS, None, httpx2.Headers()
                    )
                ),
                id="rate limited",
            ),
            pytest.param(
                lambda questions: topic_response(
                    questions, without_probability_for=THEME
                ),
                id="missing main theme probability",
            ),
            pytest.param(
                lambda questions: topic_response(questions, without_presence_for=THEME),
                id="missing presence answer",
            ),
        ],
    )
    def test_skips_only_the_track_that_failed(self, topic_df, reply_for_failing_track):
        client = FakeTypeSafeClient(reply_for_failing_track)
        lyrics_topic_df = analyze(topic_df, client, GOOD_TRACK, FAILING_TRACK)

        assert lyrics_topic_df.track_id.unique().tolist() == [GOOD_TRACK["track_id"]]

    def test_returns_an_empty_table_when_every_track_fails(self, topic_df):
        client = FakeTypeSafeClient(
            raising(TypeSafeAPITimeoutError(REQUEST_TIMEOUT_SECONDS))
        )

        assert analyze(topic_df, client, FAILING_TRACK).empty


class TestSelectUncategorized:
    def uncategorized_track_ids(self, topic_df, lyrics_topic_df):
        analyzer = LyricsTopicAnalyzer(topic_df, FakeTypeSafeClient)
        track_df = pd.DataFrame({LyricsTopicAnalyzer.TRACK_ID_COLUMN: list(TRACK_IDS)})
        return analyzer.select_uncategorized(
            track_df, lyrics_topic_df
        ).track_id.tolist()

    def lyrics_topics(self, track_id, analysis_version):
        return pd.DataFrame(
            {
                LyricsTopicAnalyzer.TRACK_ID_COLUMN: [track_id],
                LyricsTopicAnalyzer.ANALYSIS_VERSION_COLUMN: [analysis_version],
            }
        )

    def test_selects_every_track_when_nothing_is_categorized(self, topic_df):
        no_topics = self.lyrics_topics(
            GOOD_TRACK["track_id"], LyricsTopicAnalyzer.ANALYSIS_VERSION
        ).iloc[0:0]

        assert self.uncategorized_track_ids(topic_df, no_topics) == list(TRACK_IDS)

    def test_skips_tracks_categorized_in_the_current_version(self, topic_df):
        current = self.lyrics_topics(
            GOOD_TRACK["track_id"], LyricsTopicAnalyzer.ANALYSIS_VERSION
        )

        assert self.uncategorized_track_ids(topic_df, current) == [
            FAILING_TRACK["track_id"]
        ]

    def test_recategorizes_tracks_from_an_older_version(self, topic_df):
        older = self.lyrics_topics(GOOD_TRACK["track_id"], OLDER_ANALYSIS_VERSION)

        assert self.uncategorized_track_ids(topic_df, older) == list(TRACK_IDS)
