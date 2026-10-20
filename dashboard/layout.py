import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from data import (
    MIN_DISTINCTIVE_SHARE,
    WORDS_PER_RATE,
    PERCENT,
    PROFANITY_TERM,
    TOPIC_PRESENCE_THRESHOLD,
    VOCABULARY_GENRES,
)

SHARE_CHART_HEIGHT = 520
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
    explicit_df,
    emotion_df,
):
    return html.Div(
        [
            build_header(),
            build_genre_sheet(genre_df),
            build_vocabulary_sheet(
                genre_df, topic_df, genre_topic_share_df, distinctive_df, shared_words
            ),
            build_topic_sheet(topic_df, topic_presence_df),
            build_explicit_sheet(explicit_df),
            build_emotion_sheet(emotion_df),
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
    genre_df, topic_df, genre_topic_share_df, distinctive_df, shared_words
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


def build_explicit_sheet(explicit_df):
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
            build_chart_note(
                f"{format_citation(BILLBOARD_SOURCE)} and {format_citation(MELO_LYRICS_SOURCE)}"
            ),
        ],
        className="sheet",
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
    first_year = year_df["year"].min()
    last_year = year_df["year"].max()
    early_years = (first_year, first_year + PERIOD_LENGTH_YEARS - 1)
    late_years = (last_year - PERIOD_LENGTH_YEARS + 1, last_year)
    middle_years = (early_years[1] + 1, late_years[0] - 1)
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
