import logging
import os

from dynaconf import Dynaconf
from sqlalchemy import create_engine

from etl import ETLProcessor, Extractor
from lyrics_analysis import LyricsAnalyzer

os.chdir(os.path.dirname(__file__))

BILLBOARD_PATH = "data/billboard-hot100-lyrics-main"
SPOTIFY_PATH = "data/spotify_tracks.csv"
TOPIC_PATH = "data/topics.csv"

def build_engine():
        settings = Dynaconf(envvar_prefix="DB", load_dotenv=True)
        return create_engine(settings.ENGINE_URL, echo=False)

def run():
    logging.basicConfig(level=logging.NOTSET)

    engine = build_engine()

    with engine.begin() as conn:
        processor = ETLProcessor(conn, BILLBOARD_PATH, SPOTIFY_PATH, TOPIC_PATH)
        processor.process()

    engine.dispose()
    
def analyze_lyrics():
  engine = build_engine()
  
  with engine.begin() as conn:
    extractor = Extractor(conn)
    track_df = extractor.extract_from_db("track")
    
    for track in track_df.itertuples(index=False):
      analyzer = LyricsAnalyzer(track)
      lyric_metric_df, lyric_ngram_df = analyzer.analyze()

  engine.dispose()
  
    


if __name__ == "__main__":
    run()
    analyze_lyrics()
    
