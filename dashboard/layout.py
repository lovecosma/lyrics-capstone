import pandas as pd
import plotly.express as px
from dash import dcc, html

GENRE_SHARE_CHART_HEIGHT = 520
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
BILLBOARD_SOURCE = {
    "author": "Billboard",
    "date": "2000–2024",
    "title": "Year-end Hot 100 songs",
    "details": "[Data set].",
    "url": "https://www.billboard.com/charts/year-end/hot-100-songs/",
}


def build_layout(df):
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
                    dcc.Graph(figure=build_genre_share_chart(df)),
                    html.P(
                        "Country/Folk saw the largest increase of +13.6%. R&B/Soul had the largest decrease of -15.7%. "
                        "Rock/Alternative saw the next largest decrease of -10.7%. Hip-Hop/Rap had the next largest "
                        "increase of +7.3%.",
                    ),
                    build_genre_share_table(df),
                    build_chart_note(
                        f"{format_citation(BILLBOARD_SOURCE)} and "
                        f"{format_citation(APPLE_ITUNES_SOURCE)}"
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


def build_genre_share_chart(genre_year_df):
    year_totals = genre_year_df.groupby("year")["entry_count"].transform("sum")
    genre_share_df = genre_year_df.assign(
        entry_share=genre_year_df["entry_count"] / year_totals * PERCENT
    ).sort_values("year")
    figure = px.line(
        genre_share_df,
        x="year",
        y="entry_share",
        color="broad_genre",
        category_orders={"broad_genre": list(genre_order(genre_year_df))},
        labels={"year": "Year", "entry_share": "% of entries", "broad_genre": "Genre"},
        height=GENRE_SHARE_CHART_HEIGHT,
    )
    figure.update_traces(hovertemplate="%{y:.1f}%")
    figure.update_layout(hovermode="x unified", font_family=CHART_FONT_FAMILY)
    return figure


def build_genre_share_table(genre_year_df):
    first_year = genre_year_df["year"].min()
    last_year = genre_year_df["year"].max()
    early_years = (first_year, first_year + PERIOD_LENGTH_YEARS - 1)
    late_years = (last_year - PERIOD_LENGTH_YEARS + 1, last_year)
    middle_years = (early_years[1] + 1, late_years[0] - 1)
    shares = (
        pd.DataFrame(
            {
                "early": period_genre_shares(genre_year_df, *early_years),
                "middle": period_genre_shares(genre_year_df, *middle_years),
                "late": period_genre_shares(genre_year_df, *late_years),
            }
        )
        .fillna(0)
        .loc[genre_order(genre_year_df)]
    )
    shares["change"] = shares["late"] - shares["early"]

    header = html.Tr(
        [
            html.Th("Genre"),
            html.Th(format_period(*early_years)),
            html.Th(format_period(*middle_years)),
            html.Th(format_period(*late_years)),
            html.Th("Change (pts)"),
        ]
    )
    rows = [
        html.Tr(
            [
                html.Td(genre),
                html.Td(f"{row.early:.1f}%"),
                html.Td(f"{row.middle:.1f}%"),
                html.Td(f"{row.late:.1f}%"),
                html.Td(f"{row.change:+.1f}", className=change_class(row.change)),
            ]
        )
        for genre, row in shares.iterrows()
    ]
    return html.Div(
        html.Table([html.Thead(header), html.Tbody(rows)]), className="table-scroll"
    )


def genre_order(genre_year_df):
    return (
        genre_year_df.groupby("broad_genre")["entry_count"]
        .sum()
        .sort_values(ascending=False)
        .index
    )


def period_genre_shares(genre_year_df, first_year, last_year):
    period_counts = (
        genre_year_df[genre_year_df["year"].between(first_year, last_year)]
        .groupby("broad_genre")["entry_count"]
        .sum()
    )
    return period_counts / period_counts.sum() * PERCENT


def format_period(first_year, last_year):
    return f"{first_year}–{last_year}"


def change_class(change):
    if change >= FLAT_CHANGE_POINTS:
        return "change-up"
    if change <= -FLAT_CHANGE_POINTS:
        return "change-down"
    return "change-flat"
