# Presentation Planning

## Working Questions

Main question: What are trends in lyrical content and sound quality in Billboard's year end Top 100 songs from the past 25 years?

1. How did the mix of genres on the charts change?
2. Which lyrical topics dominated the charts?
3. Which lyrical topics grew and which declined over the 25 years?
4. Which lyrical topics does each genre emphasize?
5. Within Pop, did songs shift from Heartbreak & Loss toward Party & Celebration?
6. How did the vocabulary of hit songs change, and which words and phrases rose or fell?
7. Does each genre and topic have its own distinctive vocabulary?
8. Did explicit hits become more common?
9. What about the sound quality of the music changed?
10. Did hard economic times change what hit songs were about?

## Datasets

- Billboard Year-End Hot 100 lyrics (2000–2024) - GitHub, accessed October 13, 2026
  - created by Tiago de Melo
  - Link: https://github.com/tmelo-uea/billboard-hot100-lyrics/tree/main
  - Billboard Year-End Hot 100 + Genius API by 
  - Citations:
    - Melo, T. de. (2026). *Billboard Year-End Hot 100 lyrics dataset (2000–2024)* [Data set]. GitHub. Retrieved October 13, 2026, from https://github.com/tmelo-uea/billboard-hot100-lyrics
  - Shape: 2,498 rows × 4 columns
    - Rank: position on the year-end chart (1–100)
    - Musica: song title
    - Artista: artist credit, including featured artists
    - Letra: full song lyrics from the Genius API 
- Spotify 1 Million Tracks - Kaggle, accessed October 12, 2026
  - created by Amitansh Joshi
  - Link: https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks
  - Spotify audio features and song length for over 1 million tracks
  - Citation: Joshi, A. (2023). *Spotify_1Million_Tracks* [Data set]. Kaggle. Retrieved October 12, 2026, from https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks
  - Shape: 1,159,764 rows × 20 columns (one CSV)
    - artist_name: artist name
    - track_name: song title
    - track_id: Spotify track ID
    - popularity: Spotify popularity score (0–100)
    - year: release year
    - genre: Spotify genre
    - danceability: how suitable the song is for dancing (0–1)
    - energy: intensity and activity (0–1)
    - key: musical key (0 = C, 1 = C♯, and so on)
    - loudness: average loudness in decibels
    - mode: major (1) or minor (0)
    - speechiness: how much of the track is spoken words (0–1)
    - acousticness: confidence the track is acoustic (0–1)
    - instrumentalness: confidence the track has no vocals (0–1)
    - liveness: confidence the track was recorded live (0–1)
    - valence: musical positivity, from sad to happy (0–1)
    - tempo: beats per minute
    - duration_ms: song length in milliseconds
    - time_signature: beats per bar
- iTunes Search API — Apple, accessed October 16, 2026
  - created by Apple Inc.
  - Link: https://performance-partners.apple.com/search-api
  - Genres and explicit flags for each track
  - Citation: Apple Inc. (2026). *iTunes Search API* [Data set]. Retrieved October 16, 2026, from https://performance-partners.apple.com/search-api
  - Shape: 2,246 rows × 5 columns (snapshot CSV of API results)
    - title: song title
    - artist_name: artist credit
    - genre: iTunes primary genre
    - is_explicit: whether iTunes marks the track as explicit
    - genre_searched_at: when the API was searched
- Jev topic classifier — TypeSafe, accessed October 14, 2026
  - created by TypeSafe
  - Link: https://typesafe.ai/blog/introducing-system-one-models-and-jev
  - Main lyrical topic for each song, classified from its lyrics
  - Citation: TypeSafe. (2026). *Jev* (Version 1.13.0) [Computer software]. Retrieved October 14, 2026, from https://typesafe.ai/blog/introducing-system-one-models-and-jev
  - Shape: 22,451 rows × 8 columns (snapshot CSV of API results, 10 topics per song)
    - title: song title
    - artist_name: artist credit
    - topic: one of the 10 lyrical topics
    - is_primary: whether this is the song's main topic
    - primary_probability: probability this is the main topic (0–1)
    - presence_probability: probability the topic is a substantial part of the lyrics (0–1)
    - model_version: Jev model version
    - analysis_version: version of the classification run
- NRC Emotion Lexicon — Mohammad & Turney, accessed October 16, 2026
  - created by Saif M. Mohammad and Peter D. Turney
  - Link: https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm
  - Words tagged with the emotions they carry
  - Citation: Mohammad, S. M., & Turney, P. D. (2013). Crowdsourcing a word–emotion association lexicon. *Computational Intelligence, 29*(3), 436–465. https://doi.org/10.1111/j.1467-8640.2012.00460.x
  - Shape: 141,820 rows × 3 columns (tab-separated text file; 14,220 words × 10 emotions)
    - word: English word
    - emotion: one of 8 emotions (anger, anticipation, disgust, fear, joy, sadness, surprise, trust) or 2 sentiments (positive, negative)
    - association: 1 if the word carries the emotion, 0 if not
- Profanity word list — Kaggle, accessed October 16, 2026
  - created by zaberdev
  - Link: https://www.kaggle.com/datasets/zaberdev/profanity
  - Profanity words with categories and severity ratings
  - Citation: zaberdev. (n.d.). *Profanity* [Data set]. Kaggle. Retrieved October 16, 2026, from https://www.kaggle.com/datasets/zaberdev/profanity
  - Shape: 1,604 rows × 9 columns (one CSV)
    - text: the profane word or spelling
    - canonical_form_1–3: the standard words it is a variant of
    - category_1–3: type of profanity (e.g. sexual, racial slur, general insult)
    - severity_rating: average severity score (1–3)
    - severity_description: Mild, Strong or Severe
- Unemployment rate — FRED, accessed October 16, 2026
  - created by the U.S. Bureau of Labor Statistics
  - Link: https://fred.stlouisfed.org/series/UNRATE
  - Monthly US unemployment rate
  - Citation: U.S. Bureau of Labor Statistics. (2026). *Unemployment rate* [UNRATE] [Data set]. Federal Reserve Bank of St. Louis. Retrieved October 16, 2026, from https://fred.stlouisfed.org/series/UNRATE
  - Shape: 945 rows × 2 columns (monthly, 1948–2026)
    - observation_date: first day of the month
    - UNRATE: unemployment rate in percent
- Consumer sentiment — FRED, accessed October 16, 2026
  - created by the University of Michigan
  - Link: https://fred.stlouisfed.org/series/UMCSENT
  - Monthly US consumer sentiment index
  - Citation: University of Michigan. (2026). *University of Michigan: Consumer sentiment* [UMCSENT] [Data set]. Federal Reserve Bank of St. Louis. Retrieved October 16, 2026, from https://fred.stlouisfed.org/series/UMCSENT
  - Shape: 886 rows × 2 columns (monthly, 1952–2026)
    - observation_date: first day of the month
    - UMCSENT: consumer sentiment index (1966 Q1 = 100)
- Birth rate — FRED, accessed October 19, 2026
  - created by the World Bank
  - Link: https://fred.stlouisfed.org/series/SPDYNCBRTINUSA
  - Yearly US births per 1,000 people
  - Citation: World Bank. (2026). *Crude birth rate for the United States* [SPDYNCBRTINUSA] [Data set]. Federal Reserve Bank of St. Louis. Retrieved October 19, 2026, from https://fred.stlouisfed.org/series/SPDYNCBRTINUSA
  - Shape: 65 rows × 2 columns (yearly, 1960–2024)
    - observation_date: first day of the year
    - SPDYNCBRTINUSA: births per 1,000 people

## Project Management

### Extract

- Importing data — est. 6 hours, 8 hours
  - CSVs (Billboard, Spotify, NRC, profanity, FRED) and APIs (iTunes, TypeSafe) 
- Exploratory Data Analysis of each dataset — est. 6 hours, 8 hours, completed 10/19/2026

### Infrastructure: Database

- Database design (ERD, DDL) — est. 2 hours, 3 hours
  - PostgreSQL schema and SQL views for the dashboard

### Transform

- Data cleaning — est. 8 hours, 16 hours
  - Where: Airflow DAG tasks (first built in main.py)
  - How: Pandas
- ML model — not used
  - Topics come from TypeSafe's Jev model, not a model I trained

### Load

- Other data storage — est. 2 hours, 2 hours
  - Snapshot CSVs of the iTunes and TypeSafe results, so reruns don't call the APIs again

### Infrastructure: Docker and Airflow

- Docker setup — 2 hours, actual 2 hours, completed 10/21/2026
  - Postgres and Airflow containers with Docker Compose
- Airflow DAGs — est. 8 hours, actual 8 hours
  - One DAG with task groups for the ETL, lyrics analysis and genre enrichment
- ETL documentation — est. 2 hours, actual 4 hours, completed 10/22/2026
  - ETL_DOCS.md, written while moving each step into Airflow

### Dash App

- Sketches: visualizations and dashboards — est. 1 hour, actual 1 hours, completed 10/19/2026
  - CHART_PLANNING.md
- Dashboard creation — est. 8 hours, actual 10 hours, completed 10/22/2026
  - Plotly Dash, documented in dashboard/DASH_DOCS.md

### Presentation

- Presentation prep — est. 8 hours, actual TODO hours, in progress
