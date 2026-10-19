import pandas as pd
import plotly.express as px
from dash import dcc, html

from data import TOPIC_PRESENCE_THRESHOLD

SHARE_CHART_HEIGHT = 520
# Diameter in pixels of the bubble with the largest share; bubble area scales with share
BUBBLE_MAX_SIZE = 45
# Leaves room around the furthest bubbles for their labels
BUBBLE_AXIS_ROOM = 1.15
BUBBLE_FRAME_MS = 1000
BUBBLE_TRANSITION_MS = 800
CATEGORY_COLORS = px.colors.qualitative.Plotly
PERCENT = 100
PERIOD_LENGTH_YEARS = 8
FLAT_CHANGE_POINTS = 3
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
BILLBOARD_SOURCE = {
    "author": "Billboard",
    "date": "2000–2024",
    "title": "Year-end Hot 100 songs",
    "details": "[Data set].",
    "url": "https://www.billboard.com/charts/year-end/hot-100-songs/",
}


def build_layout(genre_df, topic_df, topic_presence_df):
    topic_year_totals = topic_df.groupby("year")["entry_count"].sum()
    return html.Div(
        [
            html.Header(
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
            ),
            html.Section(
                [
                    html.H2("Rising Stars: Country/Folk and Hip-Hop/Rap"),
                    html.P(
                        "Each year's Billboard Year-End Hot 100 lists about 100 songs. Each song is assigned "
                        "one genre which is its primary genre from iTunes, grouped into a broad genre. A genre's "
                        "percentage for a year is the number of that year's songs in the genre divided by "
                        "the number of that year's songs with a genre. The percent change is the difference "
                        "in percentage points between the first and last periods."
                    ),
                    dcc.Graph(figure=build_share_chart(
                            genre_df, "broad_genre", "Genre", "Share of chart entries by genre"
                        )),
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
            ),
            html.Section(
                [
                    html.H2("Love leads to Heartbreak, Money Moves In"),
                    html.P(
                        "Each song's lyrics are assigned one main topic by TypeSafe's Jev model. A topic's "
                        "percentage for a year is the number of that year's songs with that main topic "
                        "divided by the number of songs on that year's chart. Most songs also touch on other "
                        "topics: a song mentions a topic when it's the main topic or when the model is at "
                        f"least {TOPIC_PRESENCE_THRESHOLD:.0%} confident the topic is present. In the chart, "
                        "each bubble is a topic: further right means it's the main topic of more songs, and "
                        "higher means more songs mention it. Press Play to watch the topics move from "
                        f"{topic_df['year'].min()} to {topic_df['year'].max()}."
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
            ),
        ],
        className="container",
    )


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
        labels={"year": "Year", "entry_share": "% of entries", category: category_label},
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
        index="year", columns=category, values="entry_count", aggfunc="sum", fill_value=0
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
    movement_df = yearly_shares(topic_df, "main_topic").rename(
        columns={"main_topic": "topic", "entry_share": "main_share"}
    ).merge(
        yearly_shares(topic_presence_df, "topic", year_totals).rename(
            columns={"entry_share": "mention_share"}
        ),
        on=["year", "topic"],
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


def build_share_table(year_df, category, category_label, title, year_totals=None):
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
                html.Td(f"{row.change:+.1f}", className=change_class(row.change)),
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
    period_total = year_totals[year_totals.index.to_series().between(first_year, last_year)].sum()
    return period_counts / period_total * PERCENT


def format_period(first_year, last_year):
    return f"{first_year}–{last_year}"


def change_class(change):
    if change >= FLAT_CHANGE_POINTS:
        return "change-up"
    if change <= -FLAT_CHANGE_POINTS:
        return "change-down"
    return "change-flat"
