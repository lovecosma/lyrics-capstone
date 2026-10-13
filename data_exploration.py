import os

import pandas as pd

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run():
  lyric_df = pd.read_csv("data/billboard-year-end-2000-lyrics.csv")
  lyric_df.columns = ['rank', 'track_name', 'artist_name', 'lyrics']
  track_df = pd.read_csv("data/spotify_tracks.csv")
  merged_df = pd.merge(lyric_df, track_df, how="inner", on=["track_name", "artist_name"])
  print(merged_df.head())


if __name__ == "__main__":
  run()