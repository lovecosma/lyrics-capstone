import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from scipy import stats

from data import (
    MIN_DISTINCTIVE_SHARE,
    PERCENT,
    PROFANITY_TERM,
    SOUND_LAST_YEAR,
    TOPIC_PRESENCE_THRESHOLD,
    VOCABULARY_GENRES,
    WORDS_PER_RATE,
    main_topics,
)

SHARE_CHART_HEIGHT = 520
SOUND_FEATURE_LABELS = {
    "valence": "Valence",
    "energy": "Energy",
    "acousticness": "Acousticness",
    "danceability": "Danceability",
    "speechiness": "Speechiness",
}
DEFAULT_SOUND_FEATURES = ("valence", "energy", "acousticness", "danceability")
DUMBBELL_MARKER_SIZE = 14
WORD_CHANGE_COUNT = 8
RISE_COLOR = "#15803d"
FALL_COLOR = "#b91c1c"
ALL_GENRES_LABEL = "All genres"
ALL_SONGS_LABEL = "All songs"
SONG_LENGTH_LABEL = "Song length (minutes)"
SONG_LENGTH_AXIS_PADDING_MINUTES = 0.25
SOUND_FLAT_CHANGE_PERCENT = 5
BUBBLE_MAX_SIZE = 45
BUBBLE_AXIS_ROOM = 1.15
BUBBLE_FRAME_MS = 1000
BUBBLE_TRANSITION_MS = 800
CATEGORY_COLORS = px.colors.qualitative.Plotly
GENRE_VOCABULARY_CHART_ID = "genre-vocabulary-chart"
GENRE_VOCABULARY_PICKER_ID = "genre-vocabulary-picker"
GENRE_WORD_CHANGE_CHART_ID = "genre-word-change-chart"
GENRE_WORD_CHANGE_PICKER_ID = "genre-word-change-picker"
TOPIC_VOCABULARY_CHART_ID = "topic-vocabulary-chart"
TOPIC_VOCABULARY_PICKER_ID = "topic-vocabulary-picker"
TOPIC_WORD_CHANGE_CHART_ID = "topic-word-change-chart"
TOPIC_WORD_CHANGE_PICKER_ID = "topic-word-change-picker"
VOCABULARY_SHEET_CHART_HEIGHT = 460
DEFAULT_VOCABULARY_GENRE = "Country/Folk"
OTHER_GENRES_LABEL = "Other genres"
OTHER_TOPICS_LABEL = "Other topics"
OTHER_GENRES_COLOR = "#b8bdc7"
SENTIMENTS = ("Positive", "Negative")
DEFAULT_EMOTIONS = ("Positive", "Fear", "Joy", "Anger")
HEADLINE_TOPIC = "Party & Celebration"
UNEMPLOYMENT_INDICATOR = "Unemployment Rate"
ECONOMY_INDICATORS = (UNEMPLOYMENT_INDICATOR, "Consumer Sentiment", "Birth Rate")
CORRELATION_DECIMALS = 2
MAX_CORRELATION = 1
SIGNIFICANCE_LEVEL = 0.05
SIGNIFICANCE_MARKER = "*"
ECONOMY_HEATMAP_HEIGHT = 380
TOPIC_HEATMAP_DECIMALS = 0
# Emotion shares differ by fractions of a point between genres
EMOTION_HEATMAP_DECIMALS = 1
HEATMAP_COLOR_SCALE = [[0, "#e8908a"], [0.5, "#ffffff"], [1, "#7cc48c"]]
PERIOD_LENGTH_YEARS = 8
FLAT_CHANGE_POINTS = 3
EMOTION_FLAT_CHANGE_POINTS = 0.5
CHART_FONT_FAMILY = "DM Mono, monospace"
CHART_TITLE_CENTER_X = 0.5
CHART_TITLE_FONT_FAMILY = "Barlow Condensed, Arial Narrow, sans-serif"
CHART_TITLE_FONT_SIZE = 22
CHART_TITLE_FONT_WEIGHT = 600

# "author" is the in-text form; "reference_author" is the APA reference list form when they differ
APPLE_ITUNES_SOURCE = {
    "author": "Apple Inc.",
    "date": "2026",
    "title": "iTunes Search API",
    "details": "[Data set].",
    "retrieved": "October 16, 2026",
    "url": "https://performance-partners.apple.com/search-api",
}
MELO_LYRICS_SOURCE = {
    "author": "Melo",
    "reference_author": "Melo, T. de",
    "date": "2026",
    "title": "Billboard Year-End Hot 100 lyrics dataset (2000–2024)",
    "details": "[Data set]. GitHub.",
    "url": "https://github.com/tmelo-uea/billboard-hot100-lyrics",
}
TYPESAFE_SOURCE = {
    "author": "TypeSafe",
    "date": "2026",
    "title": "Jev",
    "details": "(Version 1.13.0) [Computer software].",
    "retrieved": "October 14, 2026",
    "url": "https://typesafe.ai/blog/introducing-system-one-models-and-jev",
}
NRC_EMOTION_SOURCE = {
    "author": "Mohammad & Turney",
    "reference_author": "Mohammad, S. M., & Turney, P. D.",
    "date": "2013",
    "title": "Crowdsourcing a word–emotion association lexicon",
    "journal": "Computational Intelligence, 29",
    "details": "(3), 436–465.",
    "url": "https://doi.org/10.1111/j.1467-8640.2012.00460.x",
}
BLS_UNEMPLOYMENT_SOURCE = {
    "author": "U.S. Bureau of Labor Statistics",
    "date": "2026",
    "title": "Unemployment rate",
    "details": "[UNRATE] [Data set]. Federal Reserve Bank of St. Louis.",
    "retrieved": "October 16, 2026",
    "url": "https://fred.stlouisfed.org/series/UNRATE",
}
UMICH_SENTIMENT_SOURCE = {
    "author": "University of Michigan",
    "date": "2026",
    "title": "University of Michigan: Consumer sentiment",
    "details": "[UMCSENT] [Data set]. Federal Reserve Bank of St. Louis.",
    "retrieved": "October 16, 2026",
    "url": "https://fred.stlouisfed.org/series/UMCSENT",
}
WORLD_BANK_BIRTH_RATE_SOURCE = {
    "author": "World Bank",
    "date": "2026",
    "title": "Crude birth rate for the United States",
    "details": "[SPDYNCBRTINUSA] [Data set]. Federal Reserve Bank of St. Louis.",
    "retrieved": "October 19, 2026",
    "url": "https://fred.stlouisfed.org/series/SPDYNCBRTINUSA",
}
JOSHI_SPOTIFY_SOURCE = {
    "author": "Joshi",
    "reference_author": "Joshi, A.",
    "date": "2023",
    "title": "Spotify_1Million_Tracks",
    "details": "[Data set]. Kaggle.",
    "url": "https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks",
}
BILLBOARD_SOURCE = {
    "author": "Billboard",
    "date": "2000–2024",
    "title": "Year-end Hot 100 songs",
    "details": "[Data set].",
    "url": "https://www.billboard.com/charts/year-end/hot-100-songs/",
}
ZABERDEV_PROFANITY_SOURCE = {
    "author": "zaberdev",
    "date": "n.d.",
    "title": "Profanity",
    "details": "[Data set]. Kaggle.",
    "retrieved": "October 16, 2026",
    "url": "https://www.kaggle.com/datasets/zaberdev/profanity",
}
REFERENCE_SOURCES = (
    APPLE_ITUNES_SOURCE,
    MELO_LYRICS_SOURCE,
    TYPESAFE_SOURCE,
    NRC_EMOTION_SOURCE,
    BLS_UNEMPLOYMENT_SOURCE,
    UMICH_SENTIMENT_SOURCE,
    WORLD_BANK_BIRTH_RATE_SOURCE,
    JOSHI_SPOTIFY_SOURCE,
    BILLBOARD_SOURCE,
    ZABERDEV_PROFANITY_SOURCE,
)


def build_layout(
    genre_df,
    topic_df,
    topic_presence_df,
    genre_topic_share_df,
    genre_distinctive_df,
    topic_distinctive_df,
    shared_words,
    word_year_df,
    explicit_df,
    explicit_breakdown_df,
    emotion_df,
    genre_emotion_share_df,
    sound_df,
    economy_df,
):
    return html.Div(
        [
            build_header(),
            build_genre_sheet(genre_df),
            build_topic_sheet(topic_df, topic_presence_df, genre_topic_share_df),
            build_vocabulary_sheet(
                genre_df,
                topic_df,
                genre_distinctive_df,
                topic_distinctive_df,
                shared_words,
                word_year_df,
            ),
            build_explicit_sheet(explicit_df, explicit_breakdown_df),
            build_emotion_sheet(emotion_df, genre_emotion_share_df),
            build_sound_sheet(sound_df),
            build_economy_sheet(economy_df, topic_df),
            build_references_sheet(),
        ],
        className="container",
    )


def build_header():
    return html.Header(
        [
            html.H1("Billboard Hot 100 25 Year Rewind"),
            html.P(
                "This application uses Billboard's year-end top 100 songs in US along "
                "with iTunes genre classification to explore trends in popular music "
                "in the US in the past 25 years. We examine trends in genre "
                "popularity, lyrics content, and explore whether economic health in "
                "the US influences the content of music at the top of the charts."
            ),
        ],
        className="page-header",
    )


def build_genre_sheet(genre_df):
    return html.Section(
        [
            html.H2("Rising Stars: Country/Folk and Hip-Hop/Rap"),
            html.P(
                "Each year's Billboard Year-End Hot 100 lists about 100 songs. Each "
                "song is assigned one genre which is its primary genre from iTunes and "
                "one broad genre which is a mapping of its genre to 9 broad "
                "categories. A genre's percentage for a year is the number of that "
                "year's songs in the genre divided by the number of that year's songs "
                "with a genre. The percent change is the difference in percentage "
                "points between the first and last periods."
            ),
            dcc.Graph(
                figure=build_share_chart(
                    genre_df, "broad_genre", "Genre", "Share of chart entries by genre"
                )
            ),
            html.P(
                "Country/Folk saw the largest increase of +13.0 points. R&B/Soul had "
                "the largest decrease of -15.6 points. Rock/Alternative saw the next "
                "largest decrease of -10.3 points. Hip-Hop/Rap had the next largest "
                "increase of +7.3 points.",
            ),
            build_share_table(
                genre_df, "broad_genre", "Genre", "Genre share by period"
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and "
                f"{format_citation(APPLE_ITUNES_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_vocabulary_sheet(
    genre_df,
    topic_df,
    genre_distinctive_df,
    topic_distinctive_df,
    shared_words,
    word_year_df,
):
    topics = main_topics(topic_df)
    return html.Section(
        [
            html.H2("Shared Words, Shifting Slang"),
            dcc.Tabs(
                [
                    dcc.Tab(
                        [
                            html.P(
                                "Every genre's most used words are the same: "
                                f"{', '.join(shared_words)}. What sets genres apart "
                                "are the words below: used in at least "
                                f"{MIN_DISTINCTIVE_SHARE}% of a genre's songs and far "
                                "more often than in other genres' songs. Swear words "
                                f"and slurs are grouped as {PROFANITY_TERM}."
                            ),
                            build_picker(
                                GENRE_VOCABULARY_PICKER_ID,
                                "Genre",
                                list(VOCABULARY_GENRES),
                                DEFAULT_VOCABULARY_GENRE,
                            ),
                            dcc.Graph(
                                id=GENRE_VOCABULARY_CHART_ID,
                                figure=build_vocabulary_chart(
                                    genre_distinctive_df,
                                    DEFAULT_VOCABULARY_GENRE,
                                    category_colors(genre_df, "broad_genre")[
                                        DEFAULT_VOCABULARY_GENRE
                                    ],
                                    OTHER_GENRES_LABEL,
                                ),
                            ),
                            html.P(
                                "Vocabulary also changed over time. Each bar is the "
                                "change in the share of songs using a word between the "
                                'first and last eight years. "Girl" fell from 43% of '
                                'songs to 28%, "love" from 57% to 46% and "club" from '
                                '15% to 5%. Rap slang rose. Words like "tryna" rose '
                                'from 11% to 21% and "lil" from 8% to 14%. The biggest '
                                "rise was strong profanity, from 35% of songs to 49%."
                            ),
                            build_picker(
                                GENRE_WORD_CHANGE_PICKER_ID,
                                "Genre",
                                [ALL_GENRES_LABEL, *VOCABULARY_GENRES],
                                ALL_GENRES_LABEL,
                            ),
                            dcc.Graph(
                                id=GENRE_WORD_CHANGE_CHART_ID,
                                figure=build_word_change_chart(
                                    word_year_df, "broad_genre", ALL_GENRES_LABEL
                                ),
                            ),
                        ],
                        label="By genre",
                        className="sheet-tab",
                        selected_className="sheet-tab--selected",
                    ),
                    dcc.Tab(
                        [
                            html.P(
                                "Topics have their own vocabulary too. The words below "
                                f"are used in at least {MIN_DISTINCTIVE_SHARE}% of the "
                                "songs with a main topic and far more often than in "
                                "songs with other main topics."
                            ),
                            build_picker(
                                TOPIC_VOCABULARY_PICKER_ID,
                                "Main topic",
                                topics,
                                topics[0],
                            ),
                            dcc.Graph(
                                id=TOPIC_VOCABULARY_CHART_ID,
                                figure=build_vocabulary_chart(
                                    topic_distinctive_df,
                                    topics[0],
                                    category_colors(topic_df, "main_topic")[topics[0]],
                                    OTHER_TOPICS_LABEL,
                                ),
                            ),
                            html.P(
                                "Each bar is the change in the share of songs with a "
                                "main topic using a word between the first and last "
                                "eight years."
                            ),
                            build_picker(
                                TOPIC_WORD_CHANGE_PICKER_ID,
                                "Main topic",
                                [ALL_SONGS_LABEL, *topics],
                                ALL_SONGS_LABEL,
                            ),
                            dcc.Graph(
                                id=TOPIC_WORD_CHANGE_CHART_ID,
                                figure=build_word_change_chart(
                                    word_year_df, "main_topic", ALL_SONGS_LABEL
                                ),
                            ),
                        ],
                        label="By topic",
                        className="sheet-tab",
                        selected_className="sheet-tab--selected",
                    ),
                ],
                className="sheet-tabs",
                content_className="sheet-tabs-content",
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}, "
                f"{format_citation(APPLE_ITUNES_SOURCE)} and "
                f"{format_citation(MELO_LYRICS_SOURCE)}; topics classified with "
                f"{format_citation(TYPESAFE_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_picker(picker_id, label, options, value):
    return html.Label(
        [
            html.Span(label, className="genre-picker-label"),
            dcc.Dropdown(
                id=picker_id,
                options=options,
                value=value,
                clearable=False,
                searchable=False,
            ),
        ],
        className="genre-picker",
    )


def build_topic_sheet(topic_df, topic_presence_df, genre_topic_share_df):
    topic_year_totals = topic_df.groupby("year")["entry_count"].sum()
    return html.Section(
        [
            html.H2("Love leads to Heartbreak, Money Moves In"),
            html.P(
                "Each song's lyrics are assigned one main topic by TypeSafe's Jev "
                "model. A topic's percentage for a year is the number of that year's "
                "songs with that main topic divided by the number of songs on that "
                "year's chart. Most songs also touch on other topics. A song mentions "
                "a topic when it's the main topic or when the model is at least "
                f"{TOPIC_PRESENCE_THRESHOLD:.0%} confident the topic is present."
            ),
            dcc.Graph(
                figure=build_topic_movement_chart(
                    topic_df,
                    topic_presence_df,
                    topic_year_totals,
                    "Main topic vs. topic mentioned by year",
                ),
            ),
            html.P(
                "Lifestyle & Success saw the largest increase of +11.3 points, more "
                "than doubling its share from 7.2% to 18.4%. Sex & Desire had the "
                "largest decrease of -5.1 points. Heartbreak & Loss had the next "
                "largest increase of +4.1 points. Love & Relationships saw the next "
                "largest decrease of -3.8 points."
            ),
            build_share_table(
                topic_df, "main_topic", "Topic", "Main topic share by period"
            ),
            html.P(
                "Genres differ in what they sing about. Each cell compares a genre's "
                "share of songs with a main topic against the average across all "
                "genres with that main topic. The rise of Lifestyle & Success comes "
                "from hip-hop: it sits 26 points above the average, and no other genre "
                "is more than 4 points above for that topic."
            ),
            dcc.Graph(figure=build_genre_topic_heatmap(genre_topic_share_df, topic_df)),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}, "
                f"{format_citation(APPLE_ITUNES_SOURCE)} and "
                f"{format_citation(MELO_LYRICS_SOURCE)}; topics classified with "
                f"{format_citation(TYPESAFE_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_explicit_sheet(explicit_df, explicit_breakdown_df):
    return html.Section(
        [
            html.H2("Explicit Lyrics Nearly Doubled"),
            html.P(
                "Profanity's rise was the biggest change in vocabulary. The line chart "
                f"shows how many explicit words appear per {WORDS_PER_RATE:,} lyric "
                "words each year. Explicit words are the strong profanity and slurs "
                "grouped on the vocabulary charts above. Common filler words like "
                '"the" and "you" aren\'t counted as lyric words.'
            ),
            dcc.Graph(figure=build_explicit_chart(explicit_df)),
            html.P(
                f"Explicit words nearly doubled, from 17.2 per {WORDS_PER_RATE:,} "
                "lyric words in 2000–2007 to 33.8 in 2017–2024. They held steady "
                "through 2008–2016, then jumped in 2017."
            ),
            dcc.Tabs(
                [
                    dcc.Tab(
                        [
                            dcc.Graph(
                                figure=build_explicit_breakdown_chart(
                                    explicit_breakdown_df,
                                    "broad_genre",
                                    list(VOCABULARY_GENRES),
                                    "Songs with explicit words by genre",
                                )
                            ),
                            html.P(
                                "The rise wasn't only due to hip-hop/rap growing in "
                                "popularity as one might suspect given earlier "
                                "mentioned findings of hip-hop/rap being genre "
                                "composed of 86% songs that feature explicit content. "
                                "Pop songs with explicit words more than doubled (16% "
                                "to 34%), R&B's more than doubled (26% to 58%) and "
                                "country's rose from 2% to 12%, while hip-hop, already "
                                "at 84%, reached 93%."
                            ),
                            build_explicit_breakdown_table(
                                explicit_breakdown_df,
                                "broad_genre",
                                list(VOCABULARY_GENRES),
                                "Genre",
                                ALL_GENRES_LABEL,
                                "Songs with explicit words by genre and period",
                            ),
                        ],
                        label="By genre",
                        className="sheet-tab",
                        selected_className="sheet-tab--selected",
                    ),
                    dcc.Tab(
                        [
                            dcc.Graph(
                                figure=build_explicit_breakdown_chart(
                                    explicit_breakdown_df,
                                    "main_topic",
                                    main_topics(explicit_breakdown_df),
                                    "Songs with explicit words by main topic",
                                )
                            ),
                            html.P(
                                "Explicit words spread beyond the topics you'd expect. "
                                "Love songs with explicit words went from 11% to 28%, "
                                "and heartbreak songs from 20% to 35%. Songs about "
                                "money and status, already 86% explicit, reached 96%. "
                                "Party songs went the other way, from 62% to 42%."
                            ),
                            build_explicit_breakdown_table(
                                explicit_breakdown_df,
                                "main_topic",
                                main_topics(explicit_breakdown_df),
                                "Main topic",
                                ALL_SONGS_LABEL,
                                "Songs with explicit words by main topic and period",
                            ),
                        ],
                        label="By topic",
                        className="sheet-tab",
                        selected_className="sheet-tab--selected",
                    ),
                ],
                parent_className="sheet-tabs",
                content_className="sheet-tabs-content",
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}, "
                f"{format_citation(APPLE_ITUNES_SOURCE)} and "
                f"{format_citation(MELO_LYRICS_SOURCE)}; topics classified with "
                f"{format_citation(TYPESAFE_SOURCE)}; profanity list from "
                f"{format_citation(ZABERDEV_PROFANITY_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_explicit_breakdown_chart(breakdown_df, category, categories, title):
    early_years, _, late_years = comparison_periods(breakdown_df["year"])
    period_shares = (
        explicit_period_shares(
            breakdown_df, category, (early_years, late_years), ALL_SONGS_LABEL
        )
        .loc[categories]
        .sort_values(late_years)
    )
    labels = list(period_shares.index)
    early_shares, late_shares = period_shares[early_years], period_shares[late_years]
    connector_x = [
        share
        for label in labels
        for share in (early_shares[label], late_shares[label], None)
    ]
    connector_y = [label for label in labels for _ in range(3)]
    figure = go.Figure(
        [
            go.Scatter(
                x=connector_x,
                y=connector_y,
                mode="lines",
                line={"color": OTHER_GENRES_COLOR},
                hoverinfo="skip",
                showlegend=False,
            ),
            go.Scatter(
                x=early_shares.values,
                y=labels,
                mode="markers",
                name=format_period(*early_years),
                marker={"color": OTHER_GENRES_COLOR, "size": DUMBBELL_MARKER_SIZE},
                hovertemplate="%{y}: %{x:.0f}% of songs<extra>%{fullData.name}</extra>",
            ),
            go.Scatter(
                x=late_shares.values,
                y=labels,
                mode="markers",
                name=format_period(*late_years),
                marker={"color": CATEGORY_COLORS[0], "size": DUMBBELL_MARKER_SIZE},
                hovertemplate="%{y}: %{x:.0f}% of songs<extra>%{fullData.name}</extra>",
            ),
        ]
    )
    figure.update_xaxes(
        title_text="% of songs with at least one explicit word", range=[0, PERCENT]
    )
    figure.update_layout(
        title=build_chart_title(title),
        height=VOCABULARY_SHEET_CHART_HEIGHT,
        font_family=CHART_FONT_FAMILY,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1, "x": 0},
    )
    return figure


def explicit_period_shares(breakdown_df, category, periods, total_label):
    def share(counts):
        return counts["explicit_entry_count"] / counts["entry_count"] * PERCENT

    categorized_df = breakdown_df.dropna(subset=[category])
    shares = {}
    for period in periods:
        category_counts = (
            categorized_df[categorized_df["year"].between(*period)]
            .groupby(category)[["explicit_entry_count", "entry_count"]]
            .sum()
        )
        shares[period] = pd.concat(
            [
                share(category_counts),
                pd.Series({total_label: share(category_counts.sum())}),
            ]
        )
    return pd.DataFrame(shares)


def build_explicit_breakdown_table(
    breakdown_df, category, categories, category_label, total_label, title
):
    periods = comparison_periods(breakdown_df["year"])
    early_years, _, late_years = periods
    shares = explicit_period_shares(breakdown_df, category, periods, total_label).loc[
        [*categories, total_label]
    ]
    changes = shares[late_years] - shares[early_years]
    header = html.Tr(
        [
            html.Th(category_label),
            *[html.Th(format_period(*period)) for period in periods],
            html.Th("Change (pts)"),
        ]
    )
    rows = [
        html.Tr(
            [
                html.Td(label),
                *[html.Td(f"{shares.loc[label, period]:.0f}%") for period in periods],
                html.Td(
                    f"{changes[label]:+.0f}",
                    className=change_class(changes[label], FLAT_CHANGE_POINTS),
                ),
            ]
        )
        for label in shares.index
    ]
    return html.Div(
        html.Table([html.Caption(title), html.Thead(header), html.Tbody(rows)]),
        className="table-scroll",
    )


def build_explicit_chart(explicit_df):
    figure = px.line(
        explicit_df,
        x="year",
        y="explicit_rate",
        custom_data=["explicit_song_share"],
        labels={
            "year": "Year",
            "explicit_rate": f"Explicit words per {WORDS_PER_RATE:,} words",
        },
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(
        line_color=CATEGORY_COLORS[0],
        hovertemplate=(
            "%{x}: %{y:.1f} explicit words per "
            f"{WORDS_PER_RATE:,}"
            "<br>%{customdata[0]:.0f}% of songs use at least one<extra></extra>"
        ),
    )
    figure.update_yaxes(rangemode="tozero")
    figure.update_layout(
        title=build_chart_title(
            f"Explicit words per {WORDS_PER_RATE:,} lyric words, "
            f"{format_period(explicit_df['year'].min(), explicit_df['year'].max())}"
        ),
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_emotion_sheet(emotion_df, genre_emotion_share_df):
    emotion_count_df = emotion_df.rename(columns={"word_count": "entry_count"})
    year_word_counts = emotion_df.groupby("year")["year_word_count"].first()
    early_years, _, _ = comparison_periods(emotion_df["year"])
    return html.Section(
        [
            html.H2("Fear Rises, Joy Fades"),
            html.P(
                "The NRC Emotion Lexicon tags about 6,800 English words with eight "
                "emotions and with positive or negative sentiment. Each line is the "
                "percent change in the share of lyric words tagged with an emotion, "
                f"compared with {format_period(*early_years)}. Common filler words "
                'like "the" and "you" are left out, and so is strong profanity, which '
                "the lexicon tags as anger and disgust."
            ),
            dcc.Graph(
                figure=build_emotion_chart(
                    emotion_df,
                    period_shares(
                        emotion_count_df, "emotion", year_word_counts, *early_years
                    ),
                    early_years,
                )
            ),
            html.P(
                "Even with strong profanity excluded, fear still saw the largest "
                "increase, from 3.4% of lyric words in 2000–2007 to 4.3% in 2017–2024 "
                "(+0.9 points, a 25% rise). Anger had the next largest increase (+0.7 "
                "points, up 20%). Positive words had the largest decrease (-1.1 "
                "points, down 11%), and joy fell the most relative to where it started "
                "(-0.9 points, down 13%)."
            ),
            build_share_table(
                emotion_count_df,
                "emotion",
                "Emotion",
                "Emotion word share by period",
                year_totals=year_word_counts,
                flat_change_points=EMOTION_FLAT_CHANGE_POINTS,
            ),
            html.P(
                "Genres differ in emotion too. Each cell compares a genre's share of "
                "lyric words tagged with an emotion against the average across all "
                "genres."
            ),
            dcc.Graph(
                figure=build_genre_emotion_heatmap(genre_emotion_share_df, emotion_df)
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}, "
                f"{format_citation(APPLE_ITUNES_SOURCE)} and "
                f"{format_citation(MELO_LYRICS_SOURCE)}; emotions from "
                f"{format_citation(NRC_EMOTION_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def emotion_order(emotion_df):
    return list(
        emotion_df.groupby("emotion")["word_share"]
        .mean()
        .sort_values(ascending=False)
        .index
    )


def build_emotion_chart(emotion_df, baseline_shares, baseline_years):
    change_df = emotion_df.assign(
        share_change=(
            emotion_df["word_share"] / emotion_df["emotion"].map(baseline_shares) - 1
        )
        * PERCENT
    )
    baseline_period = format_period(*baseline_years)
    figure = px.line(
        change_df.sort_values("year"),
        x="year",
        y="share_change",
        color="emotion",
        custom_data=["word_share"],
        category_orders={"emotion": emotion_order(emotion_df)},
        labels={
            "year": "Year",
            "share_change": f"% change vs. {baseline_period}",
            "emotion": "Emotion",
        },
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(
        hovertemplate="%{customdata[0]:.2f}% of lyric words (%{y:+.0f}%)"
    )
    figure.add_hline(y=0, line_color=OTHER_GENRES_COLOR, line_width=1)
    figure.update_traces(
        line_dash="dash", selector=lambda trace: trace.name in SENTIMENTS
    )
    figure.update_traces(
        visible="legendonly", selector=lambda trace: trace.name not in DEFAULT_EMOTIONS
    )
    figure.update_layout(
        title=build_chart_title(
            f"Change in emotion word share since {baseline_period}"
        ),
        hovermode="x unified",
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_sound_sheet(sound_df):
    return html.Section(
        [
            html.H2("Shorter, Calmer, Sadder-Sounding"),
            html.P(
                "Spotify scores each song's audio from 0 to 1 on measures like valence "
                "(how happy or positive it sounds), energy (how intense and active it "
                "feels) and acousticness (how much it relies on acoustic rather than "
                "electronic sound). Each line is the yearly average over the chart "
                f"entries Spotify matched. The charts stop at {SOUND_LAST_YEAR} "
                "because Spotify matched under 60% of later entries."
            ),
            dcc.Graph(figure=build_song_length_chart(sound_df)),
            dcc.Graph(figure=build_audio_feature_chart(sound_df)),
            html.P(
                "Hits got shorter, from 4.08 minutes on average in 2000–2007 to 3.45 "
                "minutes in 2015–2022 (-15%). They also sound sadder and calmer. "
                "Valence fell from 0.58 to 0.50 (-15%) and energy from 0.70 to 0.63 "
                "(-9%), while acousticness rose from 0.15 to 0.19 (+29%). Danceability "
                "barely moved (+3%), so hits stayed just as danceable."
            ),
            build_sound_table(sound_df),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}; audio features from "
                f"{format_citation(JOSHI_SPOTIFY_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_song_length_chart(sound_df):
    figure = px.line(
        sound_df,
        x="year",
        y="minutes",
        custom_data=["matched_share"],
        labels={"year": "Year", "minutes": "Average length (minutes)"},
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(
        line_color=CATEGORY_COLORS[0],
        hovertemplate=(
            "%{x}: %{y:.2f} minutes<br>%{customdata[0]:.0f}% of entries matched<extra></extra>"
        ),
    )
    figure.update_yaxes(
        range=[
            sound_df["minutes"].min() - SONG_LENGTH_AXIS_PADDING_MINUTES,
            sound_df["minutes"].max() + SONG_LENGTH_AXIS_PADDING_MINUTES,
        ]
    )
    figure.update_layout(
        title=build_chart_title(
            "Average song length, "
            f"{format_period(sound_df['year'].min(), sound_df['year'].max())}"
        ),
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_audio_feature_chart(sound_df):
    first_year = sound_df["year"].min()
    baseline_years = (first_year, first_year + PERIOD_LENGTH_YEARS - 1)
    features = list(SOUND_FEATURE_LABELS)
    baseline = sound_df[sound_df["year"].between(*baseline_years)][features].mean()
    feature_df = sound_df.melt(
        id_vars="year", value_vars=features, var_name="feature", value_name="score"
    )
    feature_df["percent_change"] = (
        feature_df["score"] / feature_df["feature"].map(baseline) - 1
    ) * PERCENT
    feature_df = feature_df.replace({"feature": SOUND_FEATURE_LABELS})
    figure = px.line(
        feature_df,
        x="year",
        y="percent_change",
        color="feature",
        custom_data=["score"],
        category_orders={"feature": list(SOUND_FEATURE_LABELS.values())},
        labels={
            "year": "Year",
            "percent_change": f"% change vs. {format_period(*baseline_years)} average",
            "feature": "Feature",
        },
        height=SHARE_CHART_HEIGHT,
    )
    default_labels = [
        SOUND_FEATURE_LABELS[feature] for feature in DEFAULT_SOUND_FEATURES
    ]
    figure.update_traces(hovertemplate="%{y:+.0f}% (score %{customdata[0]:.2f})")
    figure.update_traces(
        visible="legendonly", selector=lambda trace: trace.name not in default_labels
    )
    figure.add_hline(y=0, line_color=OTHER_GENRES_COLOR, line_width=1)
    figure.update_layout(
        title=build_chart_title(
            f"Change in Spotify audio features vs. {format_period(*baseline_years)}"
        ),
        hovermode="x unified",
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_economy_sheet(economy_df, topic_df):
    party_share = yearly_shares(topic_df, "main_topic").pivot(
        index="year", columns="main_topic", values="entry_share"
    )[HEADLINE_TOPIC]
    unemployment = economy_df.pivot(
        index="year", columns="indicator", values="value"
    ).loc[party_share.index, UNEMPLOYMENT_INDICATOR]
    party_color = category_colors(topic_df, "main_topic")[HEADLINE_TOPIC]
    return html.Section(
        [
            html.H2("Hard Times Produced Party Songs"),
            html.P(
                "When more Americans are out of work, more hits are mainly about "
                "partying. Each line shows how far a year sits above or below its own "
                "25-year average."
            ),
            dcc.Graph(
                figure=build_unemployment_party_chart(
                    unemployment, party_share, party_color
                )
            ),
            html.P(
                "Each cell is the correlation between an indicator and a topic's "
                "yearly share. Unemployment and party songs is the strongest of all 30 "
                "pairs. Birth rate's links come from its steady decline, not the "
                "topics. "
            ),
            dcc.Graph(figure=build_economy_correlation_heatmap(economy_df, topic_df)),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and "
                f"{format_citation(MELO_LYRICS_SOURCE)}; unemployment from "
                f"{format_citation(BLS_UNEMPLOYMENT_SOURCE)}, consumer sentiment from "
                f"{format_citation(UMICH_SENTIMENT_SOURCE)} and birth rate from "
                f"{format_citation(WORLD_BANK_BIRTH_RATE_SOURCE)} via FRED"
            ),
        ],
        className="sheet",
    )


def build_unemployment_party_chart(unemployment, party_share, party_color):
    correlation = stats.pearsonr(unemployment, party_share).statistic
    figure = go.Figure(
        [
            go.Scatter(
                x=party_share.index,
                y=standardize(party_share),
                customdata=party_share.values,
                name=f"{HEADLINE_TOPIC} songs",
                line={"color": party_color},
                hovertemplate="%{customdata:.1f}% of entries",
            ),
            go.Scatter(
                x=unemployment.index,
                y=standardize(unemployment),
                customdata=unemployment.values,
                name="Unemployment rate",
                line={"color": OTHER_GENRES_COLOR, "dash": "dot"},
                hovertemplate="%{customdata:.1f}% unemployed",
            ),
        ]
    )
    figure.add_hline(y=0, line_color=OTHER_GENRES_COLOR, line_width=1)
    figure.update_xaxes(title_text="Year")
    figure.update_yaxes(title_text="STD")
    figure.update_layout(
        title=build_chart_title("Party Songs vs Unemployment"),
        height=SHARE_CHART_HEIGHT,
        hovermode="x unified",
        font_family=CHART_FONT_FAMILY,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1, "x": 0},
    )
    return figure


def build_economy_correlation_heatmap(economy_df, topic_df):
    topics = list(category_order(topic_df, "main_topic"))
    topic_shares = (
        yearly_shares(topic_df, "main_topic")
        .pivot(index="year", columns="main_topic", values="entry_share")
        .reindex(columns=topics)
        .fillna(0)
    )
    indicators = economy_df.pivot(
        index="year", columns="indicator", values="value"
    ).loc[topic_shares.index, list(ECONOMY_INDICATORS)]
    results = [
        [stats.pearsonr(indicators[indicator], topic_shares[topic]) for topic in topics]
        for indicator in ECONOMY_INDICATORS
    ]
    correlations = np.array([[result.statistic for result in row] for row in results])
    p_values = np.array([[result.pvalue for result in row] for row in results])
    labels = [
        [
            f"{correlation:+.{CORRELATION_DECIMALS}f}"
            + (SIGNIFICANCE_MARKER if p_value < SIGNIFICANCE_LEVEL else "")
            for correlation, p_value in zip(correlation_row, p_value_row)
        ]
        for correlation_row, p_value_row in zip(correlations, p_values)
    ]
    figure = go.Figure(
        go.Heatmap(
            z=correlations,
            x=topics,
            y=list(ECONOMY_INDICATORS),
            customdata=p_values,
            text=labels,
            texttemplate="%{text}",
            colorscale=HEATMAP_COLOR_SCALE,
            zmid=0,
            zmin=-MAX_CORRELATION,
            zmax=MAX_CORRELATION,
            colorbar={"title": {"text": "Correlation (r)"}},
            hovertemplate="%{y} vs. %{x}<br>r = %{z:+.2f}, p = %{customdata:.3f}<extra></extra>",
        )
    )
    figure.update_yaxes(autorange="reversed")
    figure.update_xaxes(tickangle=-30)
    figure.update_layout(
        title=build_chart_title("Economic indicators vs. main topics"),
        height=ECONOMY_HEATMAP_HEIGHT,
        font_family=CHART_FONT_FAMILY,
        plot_bgcolor="white",
    )
    return figure


def standardize(series):
    return (series - series.mean()) / series.std()


def format_citation(source):
    return f"{source['author']} ({source['date']})"


def build_references_sheet():
    sources = sorted(
        REFERENCE_SOURCES, key=lambda source: reference_author(source).casefold()
    )
    return html.Section(
        [
            html.H2("References"),
            *[
                html.P(format_reference(source), className="reference")
                for source in sources
            ],
        ],
        className="sheet",
    )


def reference_author(source):
    return source.get("reference_author", source["author"])


def format_reference(source):
    author = reference_author(source).removesuffix(".")
    reference = [f"{author}. ({source['date']}). "]
    if "journal" in source:
        reference += [
            f"{source['title']}. ",
            html.Em(source["journal"]),
            f"{source['details']} ",
        ]
    else:
        reference += [html.Em(source["title"]), f" {source['details']} "]
    if "retrieved" in source:
        reference.append(f"Retrieved {source['retrieved']}, from ")
    reference += [html.A(source["url"], href=source["url"])]
    return reference


def build_chart_note(citations):
    return html.P(
        [html.Em("Note."), f" Data from {citations}."], className="chart-note"
    )


def build_share_chart(
    year_df,
    category,
    category_label,
    title,
    year_totals=None,
):
    share_df = yearly_shares(year_df, category, year_totals)
    figure = px.line(
        share_df,
        x="year",
        y="entry_share",
        color=category,
        color_discrete_map=category_colors(year_df, category),
        category_orders={category: list(category_order(year_df, category))},
        labels={
            "year": "Year",
            "entry_share": "% of entries",
            category: category_label,
        },
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(hovertemplate="%{y:.1f}%")
    figure.update_layout(
        title=build_chart_title(
            f"{title}, {format_period(year_df['year'].min(), year_df['year'].max())}"
        ),
        hovermode="x unified",
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def yearly_shares(year_df, category, year_totals=None):
    year_counts = year_df.pivot_table(
        index="year",
        columns=category,
        values="entry_count",
        aggfunc="sum",
        fill_value=0,
    )
    if year_totals is None:
        year_totals = year_counts.sum(axis="columns")
    return (
        year_counts.div(year_totals, axis="index")
        .mul(PERCENT)
        .stack()
        .rename("entry_share")
        .reset_index()
    )


def build_topic_movement_chart(topic_df, topic_presence_df, year_totals, title):
    movement_df = (
        yearly_shares(topic_df, "main_topic")
        .rename(columns={"main_topic": "topic", "entry_share": "main_share"})
        .merge(
            yearly_shares(topic_presence_df, "topic", year_totals).rename(
                columns={"entry_share": "mention_share"}
            ),
            on=["year", "topic"],
        )
    )
    figure = px.scatter(
        movement_df,
        x="main_share",
        y="mention_share",
        color="topic",
        color_discrete_map=category_colors(topic_df, "main_topic"),
        category_orders={"topic": list(category_order(topic_df, "main_topic"))},
        text="topic",
        size="main_share",
        size_max=BUBBLE_MAX_SIZE,
        animation_frame="year",
        animation_group="topic",
        range_x=[0, movement_df["main_share"].max() * BUBBLE_AXIS_ROOM],
        range_y=[0, movement_df["mention_share"].max() * BUBBLE_AXIS_ROOM],
        labels={
            "year": "Year",
            "main_share": "% of songs with it as the main topic",
            "mention_share": "% of songs mentioning it",
        },
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(
        textposition="top center",
        hovertemplate="%{text}<br>Main topic: %{x:.1f}%<br>Mentioned: %{y:.1f}%<extra></extra>",
    )
    figure.update_layout(
        title=build_chart_title(title),
        showlegend=False,
        font_family=CHART_FONT_FAMILY,
    )
    play_button = figure.layout.updatemenus[0].buttons[0]
    play_button.args[1]["frame"]["duration"] = BUBBLE_FRAME_MS
    play_button.args[1]["transition"]["duration"] = BUBBLE_TRANSITION_MS
    return figure


def build_chart_title(text):
    return {
        "text": text,
        "x": CHART_TITLE_CENTER_X,
        "xanchor": "center",
        "font": {
            "family": CHART_TITLE_FONT_FAMILY,
            "size": CHART_TITLE_FONT_SIZE,
            "weight": CHART_TITLE_FONT_WEIGHT,
        },
    }


def category_colors(year_df, category):
    categories = category_order(year_df, category)
    return {
        category_value: CATEGORY_COLORS[position % len(CATEGORY_COLORS)]
        for position, category_value in enumerate(categories)
    }


def build_word_change_chart(word_year_df, category, value):
    early_years, _, late_years = comparison_periods(word_year_df["year"])
    if value not in (ALL_GENRES_LABEL, ALL_SONGS_LABEL):
        word_year_df = word_year_df[word_year_df[category] == value]

    def period_shares(period):
        period_df = word_year_df[word_year_df["year"].between(*period)]
        period_entry_count = period_df.drop_duplicates(
            ["year", "broad_genre", "main_topic"]
        )["year_entry_count"].sum()
        return (
            period_df.groupby("word")["entry_count"].sum()
            / period_entry_count
            * PERCENT
        )

    shares = pd.DataFrame(
        {"early": period_shares(early_years), "late": period_shares(late_years)}
    ).fillna(0)
    shares["change"] = shares["late"] - shares["early"]
    biggest_changes = pd.concat(
        [
            shares.nsmallest(WORD_CHANGE_COUNT, "change"),
            shares.nlargest(WORD_CHANGE_COUNT, "change"),
        ]
    ).sort_values("change")
    figure = go.Figure(
        go.Bar(
            x=biggest_changes["change"],
            y=biggest_changes.index,
            orientation="h",
            marker_color=np.where(
                biggest_changes["change"] > 0, RISE_COLOR, FALL_COLOR
            ),
            customdata=biggest_changes[["early", "late"]].values,
            hovertemplate=(
                "%{y}: %{customdata[0]:.0f}% → %{customdata[1]:.0f}% of songs "
                "(%{x:+.1f} pts)<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title_text="Change in share of songs using the word (pts)")
    figure.update_layout(
        title=build_chart_title(
            f"Biggest changes in word use in {value}, "
            f"{format_period(*early_years)} vs. {format_period(*late_years)}"
        ),
        height=VOCABULARY_SHEET_CHART_HEIGHT,
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_genre_topic_heatmap(genre_topic_share_df, topic_df):
    return build_genre_share_heatmap(
        genre_topic_share_df,
        "main_topic",
        list(category_order(topic_df, "main_topic")),
        "genre_song_count",
        TOPIC_HEATMAP_DECIMALS,
        "%{y} (%{customdata[2]:.0f} songs)<br>%{x}: %{customdata[0]:.1f}% of songs"
        "<br>Average across genres: %{customdata[1]:.1f}%<extra></extra>",
        "Main topics by genre vs. average",
    )


def build_genre_emotion_heatmap(genre_emotion_share_df, emotion_df):
    return build_genre_share_heatmap(
        genre_emotion_share_df,
        "emotion",
        emotion_order(emotion_df),
        "genre_word_count",
        EMOTION_HEATMAP_DECIMALS,
        "%{y} (%{customdata[2]:,.0f} lyric words)<br>%{x}: %{customdata[0]:.2f}% of lyric words"
        "<br>Average across genres: %{customdata[1]:.2f}%<extra></extra>",
        "Emotions by genre vs. average",
    )


def build_genre_share_heatmap(
    share_df, category, column_order, genre_size_column, decimals, hovertemplate, title
):
    genre_order = list(
        share_df.drop_duplicates("broad_genre").sort_values(
            genre_size_column, ascending=False
        )["broad_genre"]
    )
    genre_shares = (
        share_df.pivot(index="broad_genre", columns=category, values="genre_share")
        .reindex(index=genre_order, columns=column_order)
        .fillna(0)
    )
    average_shares = share_df.groupby(category)["average_share"].first()[column_order]
    genre_sizes = share_df.groupby("broad_genre")[genre_size_column].first()[
        genre_order
    ]
    differences = genre_shares - average_shares
    largest_difference = differences.loc[list(VOCABULARY_GENRES)].abs().values.max()
    average_grid = np.broadcast_to(average_shares.values, genre_shares.shape)
    genre_size_grid = np.broadcast_to(
        genre_sizes.values[:, np.newaxis], genre_shares.shape
    )
    figure = go.Figure(
        go.Heatmap(
            z=differences.values,
            x=column_order,
            y=genre_order,
            customdata=np.dstack([genre_shares.values, average_grid, genre_size_grid]),
            text=differences.round(decimals)
            .map(lambda points: format_point_difference(points, decimals))
            .values,
            texttemplate="%{text}",
            colorscale=HEATMAP_COLOR_SCALE,
            zmid=0,
            zmin=-largest_difference,
            zmax=largest_difference,
            colorbar={
                "title": {
                    "text": "Points above or<br>below the average<br>across genres"
                }
            },
            hovertemplate=hovertemplate,
        )
    )
    figure.update_yaxes(autorange="reversed")
    figure.update_xaxes(tickangle=-30)
    figure.update_layout(
        title=build_chart_title(title),
        height=VOCABULARY_SHEET_CHART_HEIGHT,
        font_family=CHART_FONT_FAMILY,
        plot_bgcolor="white",
    )
    return figure


def format_point_difference(points, decimals):
    return f"{points:+.{decimals}f}" if points else "0"


def build_vocabulary_chart(distinctive_df, category, category_color, other_label):
    category_terms = distinctive_df[distinctive_df["category"] == category]
    comparison_df = category_terms.melt(
        id_vars="ngram",
        value_vars=["category_share", "other_share"],
        var_name="group",
        value_name="song_share",
    ).replace({"group": {"category_share": category, "other_share": other_label}})
    figure = px.bar(
        comparison_df,
        x="song_share",
        y="ngram",
        color="group",
        orientation="h",
        barmode="group",
        color_discrete_map={category: category_color, other_label: OTHER_GENRES_COLOR},
        category_orders={
            "ngram": list(category_terms["ngram"]),
            "group": [category, other_label],
        },
        labels={"song_share": "% of songs using it", "ngram": "", "group": ""},
        height=VOCABULARY_SHEET_CHART_HEIGHT,
    )
    figure.update_traces(
        hovertemplate="%{y}: %{x:.0f}% of songs<extra>%{fullData.name}</extra>"
    )
    figure.update_layout(
        title=build_chart_title(f"Most distinctive words: {category}"),
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def comparison_periods(years):
    first_year, last_year = years.min(), years.max()
    early_years = (first_year, first_year + PERIOD_LENGTH_YEARS - 1)
    late_years = (last_year - PERIOD_LENGTH_YEARS + 1, last_year)
    middle_years = (early_years[1] + 1, late_years[0] - 1)
    return early_years, middle_years, late_years


def build_sound_table(sound_df):
    periods = comparison_periods(sound_df["year"])
    measure_labels = {"minutes": SONG_LENGTH_LABEL, **SOUND_FEATURE_LABELS}
    period_averages = pd.DataFrame(
        {
            period: sound_df[sound_df["year"].between(*period)][
                list(measure_labels)
            ].mean()
            for period in periods
        }
    )
    early_years, middle_years, late_years = periods
    percent_changes = (
        period_averages[late_years] / period_averages[early_years] - 1
    ) * PERCENT
    header = html.Tr(
        [
            html.Th("Measure"),
            *[html.Th(format_period(*period)) for period in periods],
            html.Th("Change"),
        ]
    )
    rows = [
        html.Tr(
            [
                html.Td(label),
                *[
                    html.Td(f"{period_averages.loc[measure, period]:.2f}")
                    for period in periods
                ],
                html.Td(
                    f"{percent_changes[measure]:+.0f}%",
                    className=change_class(
                        percent_changes[measure], SOUND_FLAT_CHANGE_PERCENT
                    ),
                ),
            ]
        )
        for measure, label in measure_labels.items()
    ]
    return html.Div(
        html.Table(
            [html.Caption("Sound by period"), html.Thead(header), html.Tbody(rows)]
        ),
        className="table-scroll",
    )


def build_share_table(
    year_df,
    category,
    category_label,
    title,
    year_totals=None,
    flat_change_points=FLAT_CHANGE_POINTS,
):
    if year_totals is None:
        year_totals = year_df.groupby("year")["entry_count"].sum()
    early_years, middle_years, late_years = comparison_periods(year_df["year"])
    shares = (
        pd.DataFrame(
            {
                "early": period_shares(year_df, category, year_totals, *early_years),
                "middle": period_shares(year_df, category, year_totals, *middle_years),
                "late": period_shares(year_df, category, year_totals, *late_years),
            }
        )
        .fillna(0)
        .loc[category_order(year_df, category)]
    )
    shares["change"] = shares["late"] - shares["early"]

    header = html.Tr(
        [
            html.Th(category_label),
            html.Th(format_period(*early_years)),
            html.Th(format_period(*middle_years)),
            html.Th(format_period(*late_years)),
            html.Th("Change (pts)"),
        ]
    )
    rows = [
        html.Tr(
            [
                html.Td(category_value),
                html.Td(f"{row.early:.1f}%"),
                html.Td(f"{row.middle:.1f}%"),
                html.Td(f"{row.late:.1f}%"),
                html.Td(
                    f"{row.change:+.1f}",
                    className=change_class(row.change, flat_change_points),
                ),
            ]
        )
        for category_value, row in shares.iterrows()
    ]
    return html.Div(
        html.Table(
            [
                html.Caption(title),
                html.Thead(header),
                html.Tbody(rows),
            ]
        ),
        className="table-scroll",
    )


def category_order(year_df, category):
    return (
        year_df.groupby(category)["entry_count"]
        .sum()
        .sort_values(ascending=False)
        .index
    )


def period_shares(year_df, category, year_totals, first_year, last_year):
    period_counts = (
        year_df[year_df["year"].between(first_year, last_year)]
        .groupby(category)["entry_count"]
        .sum()
    )
    period_total = year_totals[
        year_totals.index.to_series().between(first_year, last_year)
    ].sum()
    return period_counts / period_total * PERCENT


def format_period(first_year, last_year):
    return f"{first_year}–{last_year}"


def change_class(change, flat_change_points):
    if change >= flat_change_points:
        return "change-up"
    if change <= -flat_change_points:
        return "change-down"
    return "change-flat"
