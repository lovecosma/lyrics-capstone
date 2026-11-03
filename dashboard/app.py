import os

import callbacks
from dash import Dash
from layout import build_layout, category_colors
from snapshot import SNAPSHOT_DIR, read_snapshot

HOST = "127.0.0.1"
PORT = 8050
DEBUG = False

os.chdir(os.path.dirname(__file__))


def create_app(data):
    genre_df = data["genre_df"]
    topic_df = data["topic_df"]
    genre_distinctive_df = data["genre_distinctive_df"]
    topic_distinctive_df = data["topic_distinctive_df"]
    word_year_df = data["word_year_df"]
    callbacks.set_data(
        genre_distinctive_df,
        topic_distinctive_df,
        category_colors(genre_df, "broad_genre"),
        category_colors(topic_df, "main_topic"),
        word_year_df,
    )

    app = Dash(title="Hot 100 Lyrics")
    app.layout = build_layout(
        genre_df,
        topic_df,
        data["topic_presence_df"],
        data["genre_topic_share_df"],
        genre_distinctive_df,
        topic_distinctive_df,
        data["shared_words"],
        word_year_df,
        data["explicit_df"],
        data["explicit_breakdown_df"],
        data["emotion_df"],
        data["genre_emotion_share_df"],
        data["sound_df"],
        data["economy_df"],
    )
    return app


app = create_app(read_snapshot(SNAPSHOT_DIR))
# WSGI entry point for gunicorn (app:server)
server = app.server

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)
