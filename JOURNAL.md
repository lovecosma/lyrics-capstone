# 10/13/2026

## Wrapping up planning 
  - Finalized proposal
  - Planned architecture
  - Pinpointed secondary datasets

## Testing NLP
  - Added tokenizer for lyrics analysis
  - Explored the need to drop artifacts from lyrics
    - It removes text the lyrics site injected, such as "Contributors… Lyrics", ticket ads, "You might also like" and "Embed".
    - It straightens curly apostrophes, drops invisible characters and lowercases everything.
    - It splits the lyrics into lines and then into words, keeping apostrophes inside words ("don't"). Blank lines are dropped.
    - lexical_diversity: MTLD from lexicalrichness. 
      - It's the average run of words before the vocabulary starts repeating heavily, so higher means more varied. Replaced unique ÷ total, which drops as songs get longer, mainly because choruses repeat.
    - Todo: Investigate downloading stopword directly as I get closer to containerizing.
    - Notice: Avoid writing bottle neck in DAG. May want to consider use Postgres COPY through psycopg instead of writing each  row.

## Transforming Tracks
  - All Billboard year-end lyric CSVs are combined into one table, with a chart_year column taken from each filename. Rows with no lyrics are dropped.
  - Normalize names. Both datasets go through the same steps:
    - Convert to lowercase.
    - Remove accents.
    - Remove punctuation.
    - Collapse repeated whitespace.
  - Drop any row whose track key or artist key is empty
  - Inner join the two tables on the track key only.
  - Exact: the artist keys are equal once spaces are removed (blink 182 = blink182).
  - Featured: the Billboard artist starts with the Spotify artist followed by a space. Billboard often runs collaborators       together without "feat.", for example Toby Keith Willie Nelson → Toby Keith
  - Drop the pair if the Spotify title contains "remix" and the Billboard title doesn't.
  - Notice: I don't use release_date so I'll likely drop it from this version.
  
### Feedback
  - Consider using Typesafe AI - https://typesafe.ai/blog/introducing-system-one-models-and-jev
  - Consider storing lyrics directly on track


# 10/14/2026

## Building classifier
- Using TypeSafe AI
  - For each song, the classifier sends the title, artist and cleaned lyrics to TypeSafe, with 10 questions attached
  - One multiple-choice question: "What is the main theme?" The options are the 10 preselected topics with a short description
  - Nine yes/no questions, one per topic: "Is this theme a substantial part of the lyrics, beyond a single passing line?" Each comes back as a probability from 0 (no) to 1 (yes)
  - We will keep all 10 questions for each song and use SQL to filter. 

## Starting ETL
- Builds simple main.py entrypoint for ETL testing - will eventually move to airflow
- Creates specialized extractor to load billboard csvs into dataframe
- TrackMerger() enriches billboard tracks with spotify data
  - builds matching keys for both datasets: titles are lowercased, stripped of accents, punctuation and spaces, and have featured-artist credits removed, with a second version of the title that also drops anything in brackets or after a dash. Artists are cut down to the main artist before any "feat.".
  - It joins Billboard and Spotify on the title key alone, which gives every Spotify track that shares a title with each Billboard row.
  - It keeps only pairs where the artist matches, either exactly or with the Spotify artist at the start of a longer Billboard artist credit, and it rejects Spotify remixes unless the Billboard title is also a remix.
  - For each Billboard row it takes the best remaining pair (exact artist first, then the earliest Spotify year) and attaches that match's Spotify columns to the row. A Billboard row with no match keeps empty Spotify columns, so every chart row comes out exactly once.
  - Re-adds sound analysis to schema since increasing match success rate
- Load Track, Genre, Chart
- Associating tracks with genre




