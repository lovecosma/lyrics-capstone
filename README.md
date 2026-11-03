# Billboard Hot 100 25 Year Rewind

What changed in the lyrics and sound of Billboard's Year-End Hot 100 from 2000 to 2024? This project loads 25 years of year-end charts and their lyrics into Postgres, enriches each song with genres, topics, emotions and audio features, and explores the trends in a Plotly Dash dashboard.

The dashboard has eight sheets: Genre, Topic, Vocabulary, Explicit, Emotion, Sound, Economy and References.

## How it works

1. **Extract:** CSVs (Billboard lyrics, Spotify tracks, NRC Emotion Lexicon, profanity list, FRED economic series) and two APIs (iTunes Search for genres and explicit flags, TypeSafe's Jev model for lyrical topics).
2. **Transform:** pandas cleans and merges tracks, tokenizes lyrics, scores lyric metrics and n-grams, and maps iTunes genres to broad genres.
3. **Load:** everything lands in the `billboard_lyrics` Postgres schema. SQL views shape it for the dashboard.
4. **Orchestrate:** one Airflow DAG runs the whole pipeline. API results are saved to snapshot CSVs
5. **Visualize:** the Dash app reads the views through repository classes and builds the sheets.

![ETL diagram](assets/Dark%20Mode%20ETL.png)

![Schema](assets/Dark%20Mode%20Schema.png)

## Project layout

| Path | What's in it |
|---|---|
| `dags/etl.py` | Airflow DAG: schema and views, ETL, lyrics analysis and genre enrichment task groups |
| `services/` | Pipeline code: extractors, processors, transformers, the loader, lyrics analysis, genre enrichment and the iTunes client |
| `main.py` | Runs the same pipeline steps locally without Airflow |
| `sql/lyrics-schema.sql` | Tables for the `billboard_lyrics` schema |
| `sql/lyrics-views.sql` | Views the dashboard queries |
| `dashboard/` | Dash app: `app.py` (entry point), `snapshot.py` (exports the data to Parquet), `data.py` (repositories), `layout.py` (sheets and charts), `callbacks.py` (picker callbacks), `assets/style.css` |
| `airflow/Dockerfile` | Airflow image with the pipeline's extra packages |
| `docker-compose.yml` | Postgres, Cloud SQL Auth Proxy, Airflow and dashboard containers |
| `dashboard/Dockerfile` | Dashboard image, served with gunicorn |
| `dashboard/deploy.sh` | Deploys the dashboard to Cloud Run |
| `tests/` | pytest specs for the transformers, analyzers and enrichers |
| `data/` | Source datasets and API snapshots (mostly git-ignored, see below) |
| `docs/` | Technical report, ETL docs, planning docs and the development journal |
| `assets/` | Diagrams and dashboard screenshots |

## Setup

### 1. Data

Most of `data/` is git-ignored, so download the source datasets into it:

| Dataset | Path |
|---|---|
| [Billboard Year-End Hot 100 lyrics](https://github.com/tmelo-uea/billboard-hot100-lyrics) | `data/billboard-hot100-lyrics-main/` |
| [Spotify 1 Million Tracks](https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks) | `data/spotify_tracks.csv` |
| [NRC Emotion Lexicon](https://saifmohammad.com/WebPages/NRC-Emotion-Lexicon.htm) | `data/NRC-Emotion-Lexicon-v0.92/emotion-lexicon.txt` |
| [Profanity](https://www.kaggle.com/datasets/zaberdev/profanity) | `data/profanity_en.csv` |
| FRED [UNRATE](https://fred.stlouisfed.org/series/UNRATE), [UMCSENT](https://fred.stlouisfed.org/series/UMCSENT), [SPDYNCBRTINUSA](https://fred.stlouisfed.org/series/SPDYNCBRTINUSA) | `data/fred/<series>.csv`, plus `data/economic_indicators.csv` with a `code,display_name,unit,description` row per series |

The word lists, `topics.csv` and `genre_mapping.csv` are checked in. The API snapshots (`itunes_track_genres.csv`, `typesafe_lyrics_topics.csv`) are created by the first run if they're missing.

### 2. Environment

Create a `.env` in the repo root:

```
DB_USER=...
DB_PASSWORD=...
DB_DATABASE=...
DB_ENGINE_URL=postgresql+psycopg://<user>:<password>@localhost:<port>/<database>
CLOUD_SQL_INSTANCE=<project>:<region>:<instance>
AIRFLOW_UID=...
TYPESAFE_AI_API_KEY=...
```

The Cloud SQL proxy uses your gcloud application default credentials (`gcloud auth application-default login`).

### 3. Run the pipeline

With Airflow:

```bash
docker compose up -d --build
```

Open Airflow at http://localhost:8080 and trigger `etl_dag`. Every task is safe to retry.

Without Airflow, create the schema and views with `sql/lyrics-schema.sql` and `sql/lyrics-views.sql`, then:

```bash
pip install -r requirements.txt
python main.py
```

### 4. Run the dashboard

The dashboard reads a Parquet snapshot of the database, so export one after each pipeline run (needs the database reachable through `DB_ENGINE_URL`):

```bash
pip install -r dashboard/requirements.txt
python dashboard/snapshot.py
```

Then run it in a container:

```bash
docker compose up -d --build dashboard
```

Or locally:

```bash
python dashboard/app.py
```

Open http://127.0.0.1:8050.

### 5. Deploy the dashboard to Cloud Run

After the one-time setup in [dashboard/DASH_DOCS.md](dashboard/DASH_DOCS.md#deploying-to-cloud-run), export a fresh snapshot and run:

```bash
./dashboard/deploy.sh
```

The deployed dashboard doesn't connect to the database, so Cloud SQL can be stopped between pipeline runs.

### Ports

| Service | Port |
|---|---|
| Local Postgres | 5434 |
| Cloud SQL Auth Proxy | 5435 |
| Airflow | 8080 |
| Dashboard | 8050 |

## Tests

```bash
pytest
```

## Docs

- [TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md): high-level summary of the project
- [ETL_DOCS.md](docs/ETL_DOCS.md): every pipeline step and class
- [dashboard/DASH_DOCS.md](dashboard/DASH_DOCS.md): the Dash app, views and repositories
- [PLANNING.md](docs/PLANNING.md): hypotheses and original plan
- [PRESENTATION_PLANNING.md](docs/PRESENTATION_PLANNING.md): working questions, datasets with citations and project time tracking.
- [JOURNAL.md](docs/JOURNAL.md): development journal

