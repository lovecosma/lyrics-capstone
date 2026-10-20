import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from scipy import stats

from data import (
    MIN_DISTINCTIVE_SHARE,
    SOUND_LAST_YEAR,
    WORDS_PER_RATE,
    PERCENT,
    PROFANITY_TERM,
    TOPIC_PRESENCE_THRESHOLD,
    VOCABULARY_GENRES,
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
# Words shown at each end of the word change chart
WORD_CHANGE_COUNT = 8
RISE_COLOR = "#15803d"
FALL_COLOR = "#b91c1c"
ALL_GENRES_LABEL = "All genres"
ALL_SONGS_LABEL = "All songs"
EXPLICIT_TOPIC_COUNT = 7
SONG_LENGTH_LABEL = "Song length (minutes)"
SONG_LENGTH_AXIS_PADDING_MINUTES = 0.25
SOUND_FLAT_CHANGE_PERCENT = 5
BUBBLE_MAX_SIZE = 45
BUBBLE_AXIS_ROOM = 1.15
BUBBLE_FRAME_MS = 1000
BUBBLE_TRANSITION_MS = 800
CATEGORY_COLORS = px.colors.qualitative.Plotly
GENRE_TOPIC_CHART_ID = "genre-topic-chart"
VOCABULARY_CHART_ID = "vocabulary-chart"
VOCABULARY_GENRE_PICKER_ID = "vocabulary-genre-picker"
VOCABULARY_SHEET_CHART_HEIGHT = 460
DEFAULT_VOCABULARY_GENRE = "Country/Folk"
OTHER_GENRES_LABEL = "Other genres"
OTHER_GENRES_COLOR = "#b8bdc7"
SENTIMENTS = ("Positive", "Negative")
DEFAULT_EMOTIONS = ("Positive", "Negative", "Joy", "Anger")
HEADLINE_TOPIC = "Party & Celebration"
UNEMPLOYMENT_INDICATOR = "Unemployment Rate"
HEATMAP_COLOR_SCALE = [[0, "#e8908a"], [0.5, "#ffffff"], [1, "#7cc48c"]]
PERIOD_LENGTH_YEARS = 8
FLAT_CHANGE_POINTS = 3
EMOTION_FLAT_CHANGE_POINTS = 0.5
CHART_FONT_FAMILY = "DM Mono, monospace"
CHART_TITLE_CENTER_X = 0.5
CHART_TITLE_FONT_FAMILY = "Barlow Condensed, Arial Narrow, sans-serif"
CHART_TITLE_FONT_SIZE = 22
CHART_TITLE_FONT_WEIGHT = 600

APPLE_ITUNES_SOURCE = {
    "author": "Apple Inc.",
    "date": "2026",
    "title": "iTunes Search API",
    "details": "[Data set]. Retrieved October 16, 2026, from",
    "url": "https://performance-partners.apple.com/search-api",
}
MELO_LYRICS_SOURCE = {
    "author": "Melo",
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
    "url": None,
}
NRC_EMOTION_SOURCE = {
    "author": "Mohammad & Turney",
    "date": "2013",
    "title": "Crowdsourcing a word–emotion association lexicon",
    "details": "Computational Intelligence, 29(3), 436–465.",
    "url": "https://doi.org/10.1111/j.1467-8640.2012.00460.x",
}
BLS_UNEMPLOYMENT_SOURCE = {
    "author": "U.S. Bureau of Labor Statistics",
    "date": "2026",
    "title": "Unemployment rate",
    "details": "[UNRATE] [Data set]. Federal Reserve Bank of St. Louis.",
    "url": "https://fred.stlouisfed.org/series/UNRATE",
}
JOSHI_SPOTIFY_SOURCE = {
    "author": "Joshi",
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


def build_layout(
    genre_df,
    topic_df,
    topic_presence_df,
    genre_topic_share_df,
    distinctive_df,
    shared_words,
    word_year_df,
    explicit_df,
    explicit_breakdown_df,
    emotion_df,
    sound_df,
    economy_df,
):
    return html.Div(
        [
            build_header(),
            build_genre_sheet(genre_df),
            build_vocabulary_sheet(
                genre_df,
                topic_df,
                genre_topic_share_df,
                distinctive_df,
                shared_words,
                word_year_df,
            ),
            build_explicit_sheet(explicit_df, explicit_breakdown_df),
            build_topic_sheet(topic_df, topic_presence_df),
            build_emotion_sheet(emotion_df),
            build_sound_sheet(sound_df),
            build_economy_sheet(economy_df, topic_df),
        ],
        className="container",
    )


def build_header():
    return html.Header(
        [
            html.H1("Billboard Hot 100 25 Year Rewind"),
            html.P(
                "This application uses Billboard's year-end top 100 songs in US along with iTunes genre classification "
                "to explore trends in popular music in the US in the past 25 years. We examine trends in genre popularity, "
                "lyrics content, and explore whether economic health in the US influences the content of music at the "
                "top of the charts."
            ),
        ],
        className="page-header",
    )


def build_genre_sheet(genre_df):
    return html.Section(
        [
            html.H2("Rising Stars: Country/Folk and Hip-Hop/Rap"),
            html.P(
                "Each year's Billboard Year-End Hot 100 lists about 100 songs. Each song is assigned "
                "one genre which is its primary genre from iTunes, grouped into a broad genre. A genre's "
                "percentage for a year is the number of that year's songs in the genre divided by "
                "the number of that year's songs with a genre. The percent change is the difference "
                "in percentage points between the first and last periods."
            ),
            dcc.Graph(
                figure=build_share_chart(
                    genre_df, "broad_genre", "Genre", "Share of chart entries by genre"
                )
            ),
            html.P(
                "Country/Folk saw the largest increase of +13.6 points. R&B/Soul had the largest decrease of -15.7 points. "
                "Rock/Alternative saw the next largest decrease of -10.7 points. Hip-Hop/Rap had the next largest "
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
    genre_df, topic_df, genre_topic_share_df, distinctive_df, shared_words, word_year_df
):
    return html.Section(
        [
            html.H2("Every Genre Tells a Different Story"),
            html.P(
                "Genres differ in what they sing about and in how they say it. Each cell compares "
                "a genre's share of songs with a main topic against the average across all genres: "
                "green means the genre sings about it more than average, red means less, in "
                "percentage points."
            ),
            dcc.Graph(
                id=GENRE_TOPIC_CHART_ID,
                figure=build_genre_topic_heatmap(genre_topic_share_df, topic_df),
            ),
            html.P(
                f"Every genre's most used words are the same: {', '.join(shared_words)}. What sets "
                "genres apart are the words below: used in at least "
                f"{MIN_DISTINCTIVE_SHARE}% of a genre's songs and far more often than in other "
                f"genres' songs. Swear words and slurs are grouped as {PROFANITY_TERM}."
            ),
            html.Label(
                [
                    html.Span("Genre", className="genre-picker-label"),
                    dcc.Dropdown(
                        id=VOCABULARY_GENRE_PICKER_ID,
                        options=list(VOCABULARY_GENRES),
                        value=DEFAULT_VOCABULARY_GENRE,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="genre-picker",
            ),
            dcc.Graph(
                id=VOCABULARY_CHART_ID,
                figure=build_vocabulary_chart(
                    distinctive_df,
                    DEFAULT_VOCABULARY_GENRE,
                    category_colors(genre_df, "broad_genre")[DEFAULT_VOCABULARY_GENRE],
                ),
            ),
            html.P(
                "Vocabulary also changed over time. Each bar is the change in the share of songs "
                "using a word between the first and last eight years. \"Girl\" fell from 43% of "
                "songs to 28%, \"love\" from 57% to 46% and \"club\" from 15% to 5%. Rap slang "
                "rose: \"tryna\" from 11% to 21% and \"lil\" from 8% to 14%. The biggest rise was "
                "strong profanity, from 35% of songs to 49%."
            ),
            dcc.Graph(figure=build_word_change_chart(word_year_df)),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)}, {format_citation(APPLE_ITUNES_SOURCE)} "
                f"and {format_citation(MELO_LYRICS_SOURCE)}; topics classified with "
                f"{format_citation(TYPESAFE_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_topic_sheet(topic_df, topic_presence_df):
    topic_year_totals = topic_df.groupby("year")["entry_count"].sum()
    return html.Section(
        [
            html.H2("Love leads to Heartbreak, Money Moves In"),
            html.P(
                "Each song's lyrics are assigned one main topic by TypeSafe's Jev model. A topic's "
                "percentage for a year is the number of that year's songs with that main topic "
                "divided by the number of songs on that year's chart. Most songs also touch on other "
                "topics: a song mentions a topic when it's the main topic or when the model is at "
                f"least {TOPIC_PRESENCE_THRESHOLD:.0%} confident the topic is present. In the chart, "
                "each bubble is a topic: further right means it's the main topic of more songs, and "
                "higher means more songs mention it."
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
                "Lifestyle & Success saw the largest increase of +11.3 points, more than "
                "doubling its share from 7.2% to 18.4%. Sex & Desire had "
                "the largest decrease of -5.1 points. Heartbreak & Loss had the next largest "
                "increase of +4.1 points. Love & Relationships saw the next largest decrease of "
                "-3.8 points."
            ),
            build_share_table(
                topic_df, "main_topic", "Topic", "Main topic share by period"
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and "
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
                f"The line shows how many explicit words appear per {WORDS_PER_RATE:,} lyric words "
                "each year. Explicit words are the strong profanity and slurs grouped on the "
                'vocabulary chart above. Common filler words like "the" and "you" aren\'t '
                "counted as lyric words."
            ),
            dcc.Graph(figure=build_explicit_chart(explicit_df)),
            html.P(
                f"Explicit words nearly doubled, from 17.2 per {WORDS_PER_RATE:,} lyric words in "
                "2000–2007 to 33.8 in 2017–2024. They held steady through 2008–2016, then jumped in "
                "2017. The share of songs using at least one rose from 35% to 49%."
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
                                "The rise wasn't just hip-hop growing. Pop songs with explicit words "
                                "more than doubled (15% to 34%), R&B's more than doubled (25% to "
                                "57%) and country's rose from 2% to 12%, while hip-hop, already at "
                                "84%, reached 94%."
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
                                    explicit_topics(explicit_breakdown_df),
                                    "Songs with explicit words by main topic",
                                )
                            ),
                            html.P(
                                "Explicit words spread beyond the topics you'd expect. Love songs "
                                "with explicit words went from 11% to 28%, and heartbreak songs from "
                                "20% to 35%. Songs about money and status, already 86% explicit, "
                                "reached 96%. Party songs went the other way, from 62% to 42%."
                            ),
                            build_explicit_breakdown_table(
                                explicit_breakdown_df,
                                "main_topic",
                                explicit_topics(explicit_breakdown_df),
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
                f"{format_citation(BILLBOARD_SOURCE)}, {format_citation(APPLE_ITUNES_SOURCE)} "
                f"and {format_citation(MELO_LYRICS_SOURCE)}; topics classified with "
                f"{format_citation(TYPESAFE_SOURCE)}"
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


def explicit_topics(breakdown_df):
    return list(
        breakdown_df.groupby("main_topic")["entry_count"]
        .sum()
        .nlargest(EXPLICIT_TOPIC_COUNT)
        .index
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


def build_emotion_sheet(emotion_df):
    return html.Section(
        [
            html.H2("Fear Rises, Joy Fades"),
            html.P(
                "The NRC Emotion Lexicon tags about 6,800 English words with eight emotions and with "
                "positive or negative sentiment. Each line is the share of that year's lyric words "
                'tagged with an emotion. Common filler words like "the" and "you" are left out, '
                "and so is strong profanity, which the lexicon tags as anger and disgust."
            ),
            dcc.Graph(figure=build_emotion_chart(emotion_df)),
            html.P(
                "Fear saw the largest increase, from 3.4% of lyric words in 2000–2007 to 4.3% in "
                "2017–2024 (+0.9 points, a 25% rise). Anger had the next largest increase (+0.7 "
                "points). Positive words had the largest decrease (-1.1 points), and joy fell by "
                "-0.9 points. Sadness, disgust and negative words barely changed once profanity is "
                "left out."
            ),
            build_share_table(
                emotion_df.rename(columns={"word_count": "entry_count"}),
                "emotion",
                "Emotion",
                "Emotion word share by period",
                year_totals=emotion_df.groupby("year")["year_word_count"].first(),
                flat_change_points=EMOTION_FLAT_CHANGE_POINTS,
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and {format_citation(MELO_LYRICS_SOURCE)}; "
                f"emotions from {format_citation(NRC_EMOTION_SOURCE)}"
            ),
        ],
        className="sheet",
    )


def build_emotion_chart(emotion_df):
    emotion_order = list(
        emotion_df.groupby("emotion")["word_share"]
        .mean()
        .sort_values(ascending=False)
        .index
    )
    figure = px.line(
        emotion_df.sort_values("year"),
        x="year",
        y="word_share",
        color="emotion",
        category_orders={"emotion": emotion_order},
        labels={"year": "Year", "word_share": "% of lyric words", "emotion": "Emotion"},
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(hovertemplate="%{y:.2f}%")
    figure.update_traces(
        line_dash="dash", selector=lambda trace: trace.name in SENTIMENTS
    )
    figure.update_traces(
        visible="legendonly", selector=lambda trace: trace.name not in DEFAULT_EMOTIONS
    )
    figure.update_layout(
        title=build_chart_title(
            "Emotion words as a share of lyrics, "
            f"{format_period(emotion_df['year'].min(), emotion_df['year'].max())}"
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
                "Spotify scores each song's audio from 0 to 1 on measures like valence (how "
                "happy or positive it sounds), energy (how intense and active it feels) and "
                "acousticness (how much it relies on acoustic rather than electronic sound). "
                "Each line is the yearly average over the chart entries Spotify matched. The "
                f"charts stop at {SOUND_LAST_YEAR} because Spotify matched under 60% of later "
                "entries; hover to see each year's match rate."
            ),
            dcc.Graph(figure=build_song_length_chart(sound_df)),
            dcc.Graph(figure=build_audio_feature_chart(sound_df)),
            html.P(
                "Hits got shorter, from 4.08 minutes on average in 2000–2007 to 3.45 minutes in "
                "2015–2022 (-15%). They also sound sadder and calmer: valence fell from 0.59 to "
                "0.50 (-15%) and energy from 0.70 to 0.63 (-9%), while acousticness rose from 0.14 "
                "to 0.19 (+31%). Danceability barely moved (+3%), so hits stayed just as danceable."
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
                "When more Americans are out of work, more hits are mainly about partying. Each line "
                "shows how far a year sits above or below its own 25-year average."
            ),
            dcc.Graph(
                figure=build_unemployment_party_chart(
                    unemployment, party_share, party_color
                )
            ),
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and {format_citation(MELO_LYRICS_SOURCE)}; "
                f"unemployment from {format_citation(BLS_UNEMPLOYMENT_SOURCE)} via FRED"
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
    figure.update_yaxes(
        title_text="Above or below the 25-year average (standard deviations)"
    )
    figure.update_layout(
        title=build_chart_title(
            f"Party songs and unemployment move together (r = {correlation:.2f})"
        ),
        height=SHARE_CHART_HEIGHT,
        hovermode="x unified",
        font_family=CHART_FONT_FAMILY,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1, "x": 0},
    )
    return figure


def standardize(series):
    return (series - series.mean()) / series.std()


def format_citation(source):
    return f"{source['author']} ({source['date']})"


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


def build_word_change_chart(word_year_df):
    early_years, _, late_years = comparison_periods(word_year_df["year"])

    def period_shares(period):
        period_df = word_year_df[word_year_df["year"].between(*period)]
        period_entry_count = period_df.drop_duplicates("year")["year_entry_count"].sum()
        return period_df.groupby("word")["entry_count"].sum() / period_entry_count * PERCENT

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
            marker_color=np.where(biggest_changes["change"] > 0, RISE_COLOR, FALL_COLOR),
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
            "Biggest changes in word use, "
            f"{format_period(*early_years)} vs. {format_period(*late_years)}"
        ),
        height=VOCABULARY_SHEET_CHART_HEIGHT,
        font_family=CHART_FONT_FAMILY,
    )
    return figure


def build_genre_topic_heatmap(genre_topic_share_df, topic_df):
    genre_order = list(
        genre_topic_share_df.drop_duplicates("broad_genre").sort_values(
            "genre_song_count", ascending=False
        )["broad_genre"]
    )
    topic_order = list(category_order(topic_df, "main_topic"))
    genre_shares = (
        genre_topic_share_df.pivot(
            index="broad_genre", columns="main_topic", values="genre_share"
        )
        .reindex(index=genre_order, columns=topic_order)
        .fillna(0)
    )
    average_shares = genre_topic_share_df.groupby("main_topic")[
        "average_share"
    ].first()[topic_order]
    song_counts = genre_topic_share_df.groupby("broad_genre")[
        "genre_song_count"
    ].first()[genre_order]
    differences = genre_shares - average_shares
    largest_difference = differences.loc[list(VOCABULARY_GENRES)].abs().values.max()
    average_grid = np.broadcast_to(average_shares.values, genre_shares.shape)
    song_count_grid = np.broadcast_to(
        song_counts.values[:, np.newaxis], genre_shares.shape
    )
    figure = go.Figure(
        go.Heatmap(
            z=differences.values,
            x=topic_order,
            y=genre_order,
            customdata=np.dstack([genre_shares.values, average_grid, song_count_grid]),
            text=differences.round().astype(int).map(format_point_difference).values,
            texttemplate="%{text}",
            colorscale=HEATMAP_COLOR_SCALE,
            zmid=0,
            zmin=-largest_difference,
            zmax=largest_difference,
            colorbar={"title": {"text": "pts vs. avg"}},
            hovertemplate=(
                "%{y} (%{customdata[2]:.0f} songs)<br>%{x}: %{customdata[0]:.1f}% of songs"
                "<br>Average across genres: %{customdata[1]:.1f}%<extra></extra>"
            ),
        )
    )
    figure.update_yaxes(autorange="reversed")
    figure.update_xaxes(tickangle=-30)
    figure.update_layout(
        title=build_chart_title("Main topics by genre vs. average"),
        height=VOCABULARY_SHEET_CHART_HEIGHT,
        font_family=CHART_FONT_FAMILY,
        plot_bgcolor="white",
    )
    return figure


def format_point_difference(points):
    return f"{points:+d}" if points else "0"


def build_vocabulary_chart(distinctive_df, genre, genre_color):
    genre_terms = distinctive_df[distinctive_df["broad_genre"] == genre]
    comparison_df = genre_terms.melt(
        id_vars="ngram",
        value_vars=["genre_share", "other_share"],
        var_name="group",
        value_name="song_share",
    ).replace({"group": {"genre_share": genre, "other_share": OTHER_GENRES_LABEL}})
    figure = px.bar(
        comparison_df,
        x="song_share",
        y="ngram",
        color="group",
        orientation="h",
        barmode="group",
        color_discrete_map={genre: genre_color, OTHER_GENRES_LABEL: OTHER_GENRES_COLOR},
        category_orders={
            "ngram": list(genre_terms["ngram"]),
            "group": [genre, OTHER_GENRES_LABEL],
        },
        labels={"song_share": "% of songs using it", "ngram": "", "group": ""},
        height=VOCABULARY_SHEET_CHART_HEIGHT,
    )
    figure.update_traces(
        hovertemplate="%{y}: %{x:.0f}% of songs<extra>%{fullData.name}</extra>"
    )
    figure.update_layout(
        title=build_chart_title(f"Most distinctive words: {genre}"),
        font_family=CHART_FONT_FAMILY,
    )
    return figure


# The first and last PERIOD_LENGTH_YEARS years, and the years between
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
