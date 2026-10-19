import pandas as pd
import plotly.express as px
from dash import dcc, html

from data import TOPIC_PRESENCE_THRESHOLD

SHARE_CHART_HEIGHT = 520
PERCENT = 100
PERIOD_LENGTH_YEARS = 8
FLAT_CHANGE_POINTS = 3
CHART_FONT_FAMILY = "IBM Plex Mono, monospace"

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
                    dcc.Graph(figure=build_share_chart(genre_df, "broad_genre", "Genre")),
                    html.P(
                        "Country/Folk saw the largest increase of +13.6 points. R&B/Soul had the largest decrease of -15.7 points. "
                        "Rock/Alternative saw the next largest decrease of -10.7 points. Hip-Hop/Rap had the next largest "
                        "increase of +7.3 points.",
                    ),
                    build_share_table(genre_df, "broad_genre", "Genre"),
                    build_chart_note(
                        f"{format_citation(BILLBOARD_SOURCE)} and "
                        f"{format_citation(APPLE_ITUNES_SOURCE)}"
                    ),
                ],
                className="sheet",
            ),
            html.Section(
                [
                    html.H2("Lyrical topics by year"),
                    dcc.Tabs(
                        [
                            dcc.Tab(
                                [
                                    html.P(
                                        "Each song's lyrics are assigned one main topic by TypeSafe's Jev model. A topic's "
                                        "percentage for a year is the number of that year's songs with that main topic "
                                        "divided by the number of songs on that year's chart."
                                    ),
                                    dcc.Graph(
                                        figure=build_share_chart(
                                            topic_df, "main_topic", "Topic", stacked=True
                                        )
                                    ),
                                    html.P(
                                        "Lifestyle & Success saw the largest increase of +11.3 points. Sex & Desire had "
                                        "the largest decrease of -5.1 points. Heartbreak & Loss had the next largest "
                                        "increase of +4.1 points. Love & Relationships saw the next largest decrease of "
                                        "-3.8 points."
                                    ),
                                    build_share_table(topic_df, "main_topic", "Topic"),
                                ],
                                label="Main Topic",
                                className="table-tab",
                                selected_className="table-tab--selected",
                            ),
                            dcc.Tab(
                                [
                                    html.P(
                                        "Most songs touch on more than one topic. Here a topic counts for a song when it "
                                        "is the song's main topic or when the model is at least "
                                        f"{TOPIC_PRESENCE_THRESHOLD:.0%} confident the topic is present. A topic's "
                                        "percentage for a year is the number of that year's songs touching on it divided "
                                        "by the number of songs on that year's chart."
                                    ),
                                    dcc.Graph(
                                        figure=build_share_chart(
                                            topic_presence_df,
                                            "topic",
                                            "Topic",
                                            year_totals=topic_year_totals,
                                        )
                                    ),
                                    html.P(
                                        "Empowerment & Confidence saw the largest increase of +6.6 points. Love & "
                                        "Relationships had the largest decrease of -6.1 points. Lifestyle & Success had "
                                        "the next largest increase of +5.1 points. Self-Reflection & Growth saw the next "
                                        "largest decrease of only -1.0 points."
                                    ),
                                    build_share_table(
                                        topic_presence_df,
                                        "topic",
                                        "Topic",
                                        year_totals=topic_year_totals,
                                    ),
                                ],
                                label="Topic Mentioned",
                                className="table-tab",
                                selected_className="table-tab--selected",
                            ),
                        ],
                        parent_className="table-tabs",
                        content_className="table-tabs-content",
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


def build_share_chart(year_df, category, category_label, stacked=False, year_totals=None):
    year_counts = year_df.pivot_table(
        index="year", columns=category, values="entry_count", aggfunc="sum", fill_value=0
    )
    if year_totals is None:
        year_totals = year_counts.sum(axis="columns")
    share_df = (
        year_counts.div(year_totals, axis="index")
        .mul(PERCENT)
        .stack()
        .rename("entry_share")
        .reset_index()
    )
    plot = px.area if stacked else px.line
    figure = plot(
        share_df,
        x="year",
        y="entry_share",
        color=category,
        category_orders={category: list(category_order(year_df, category))},
        labels={"year": "Year", "entry_share": "% of entries", category: category_label},
        height=SHARE_CHART_HEIGHT,
    )
    figure.update_traces(hovertemplate="%{y:.1f}%")
    figure.update_layout(hovermode="x unified", font_family=CHART_FONT_FAMILY)
    if stacked:
        figure.update_yaxes(range=[0, PERCENT])
    return figure


def build_share_table(year_df, category, category_label, year_totals=None):
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
        html.Table([html.Thead(header), html.Tbody(rows)]), className="table-scroll"
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
