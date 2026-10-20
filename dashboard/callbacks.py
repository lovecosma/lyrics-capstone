from dash import Input, Output, callback
from layout import VOCABULARY_CHART_ID, VOCABULARY_GENRE_PICKER_ID, build_vocabulary_chart

distinctive_df = None
genre_colors = None


def set_data(new_distinctive_df, new_genre_colors):
    global distinctive_df, genre_colors
    distinctive_df = new_distinctive_df
    genre_colors = new_genre_colors


@callback(
    Output(VOCABULARY_CHART_ID, "figure"),
    Input(VOCABULARY_GENRE_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_vocabulary_chart(genre):
    return build_vocabulary_chart(distinctive_df, genre, genre_colors[genre])
