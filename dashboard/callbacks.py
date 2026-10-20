from dash import Input, Output, callback, no_update
from layout import (
    GENRE_TOPIC_CHART_ID,
    VOCABULARY_CHART_ID,
    VOCABULARY_GENRE_PICKER_ID,
    build_vocabulary_chart,
)

from data import VOCABULARY_GENRES

distinctive_df = None
genre_colors = None


def set_data(new_distinctive_df, new_genre_colors):
    global distinctive_df, genre_colors
    distinctive_df = new_distinctive_df
    genre_colors = new_genre_colors


# Clicking a heatmap row sets the picker, so the picker always shows the charted genre
@callback(
    Output(VOCABULARY_GENRE_PICKER_ID, "value"),
    Input(GENRE_TOPIC_CHART_ID, "clickData"),
    prevent_initial_call=True,
)
def select_clicked_genre(click_data):
    genre = click_data["points"][0]["y"]
    # Smaller genres have too few songs for a reliable word list
    if genre not in VOCABULARY_GENRES:
        return no_update
    return genre


@callback(
    Output(VOCABULARY_CHART_ID, "figure"),
    Input(VOCABULARY_GENRE_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_vocabulary_chart(genre):
    return build_vocabulary_chart(distinctive_df, genre, genre_colors[genre])
