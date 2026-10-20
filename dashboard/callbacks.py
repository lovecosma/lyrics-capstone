from dash import Input, Output, callback
from layout import (
    GENRE_VOCABULARY_CHART_ID,
    GENRE_VOCABULARY_PICKER_ID,
    GENRE_WORD_CHANGE_CHART_ID,
    GENRE_WORD_CHANGE_PICKER_ID,
    OTHER_GENRES_LABEL,
    OTHER_TOPICS_LABEL,
    TOPIC_VOCABULARY_CHART_ID,
    TOPIC_VOCABULARY_PICKER_ID,
    TOPIC_WORD_CHANGE_CHART_ID,
    TOPIC_WORD_CHANGE_PICKER_ID,
    build_vocabulary_chart,
    build_word_change_chart,
)

genre_distinctive_df = None
topic_distinctive_df = None
genre_colors = None
topic_colors = None
word_year_df = None


def set_data(
    new_genre_distinctive_df,
    new_topic_distinctive_df,
    new_genre_colors,
    new_topic_colors,
    new_word_year_df,
):
    global genre_distinctive_df, topic_distinctive_df, genre_colors, topic_colors
    global word_year_df
    genre_distinctive_df = new_genre_distinctive_df
    topic_distinctive_df = new_topic_distinctive_df
    genre_colors = new_genre_colors
    topic_colors = new_topic_colors
    word_year_df = new_word_year_df


@callback(
    Output(GENRE_VOCABULARY_CHART_ID, "figure"),
    Input(GENRE_VOCABULARY_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_genre_vocabulary_chart(genre):
    return build_vocabulary_chart(
        genre_distinctive_df, genre, genre_colors[genre], OTHER_GENRES_LABEL
    )


@callback(
    Output(TOPIC_VOCABULARY_CHART_ID, "figure"),
    Input(TOPIC_VOCABULARY_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_topic_vocabulary_chart(topic):
    return build_vocabulary_chart(
        topic_distinctive_df, topic, topic_colors[topic], OTHER_TOPICS_LABEL
    )


@callback(
    Output(GENRE_WORD_CHANGE_CHART_ID, "figure"),
    Input(GENRE_WORD_CHANGE_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_genre_word_change_chart(genre):
    return build_word_change_chart(word_year_df, "broad_genre", genre)


@callback(
    Output(TOPIC_WORD_CHANGE_CHART_ID, "figure"),
    Input(TOPIC_WORD_CHANGE_PICKER_ID, "value"),
    prevent_initial_call=True,
)
def update_topic_word_change_chart(topic):
    return build_word_change_chart(word_year_df, "main_topic", topic)
