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

# 10/15/2026

## Completing ETL
- Adding Track Genres and Chart Tracks
- Adds Topics
  - Store topics in CSV

## Implementing Lyric Metrics
  - Scrubs non content from lyrics
  - uses copy to bulk load to DB
  - splits tracks into batches
  - Moved building_blocks.py logic into LyricsAnalyzer
    - Built once so the stopword lists load once, then analyzes a whole batch of tracks
    - Returns lyrics_metric and lyrics_ngram_metric DataFrames keyed by track_id
  - Batches of 500 tracks, one load per table per batch instead of a write per track
  - Loader.copy_to_db streams rows with Postgres COPY through psycopg
    - One statement per batch instead of an INSERT per row. Matters for lyrics_ngram_metric (~1M rows)
    - Runs in the same transaction as the rest of the load
    - NaN converted to null first, otherwise numeric columns store 'NaN'

## Logging
  - Logging set up in main so it works when run() is commented out
  - Added timestamps, lyrics batch progress, transformer row counts and how many tracks link to a genre/chart
  - Warns when tracks have no words left after cleaning

## Checking Lyric Metrics
  - Every track has a metric row. Median 441 words, 125 unique, MTLD 29.6, avg word length 3.71
  - Outliers make sense: Animals (8 words), Harlem Shake and Baby Shark (lowest MTLD), Gangnam Style (shortest words)
  - MTLD barely correlates with song length (-0.05), which is why I switched away from unique ÷ total
  - Average word count drops each decade: 516 (2000s) → 462 (2010s) → 423 (2020s)
  - Found problems:
    - Unbracketed section headers ("Verse 1:") leak words like verse/hook/chorus into a few tracks
  - Fixed duplicate songs by editing the Billboard CSVs so every chart row of a song uses the spelling from its earliest chart year (11 rows)
    - Includes "&" / "-" / double space differences in artist names, e.g. "Baby Bash  Frankie J"
    - Briefly did this in TrackMerger, but removed it in favor of fixing the source data
    - 2259 → 2248 tracks, all 2484 chart rows still link to a track

## Track Matching
  - TrackMerger rejects alternate Spotify recordings unless the Billboard title is also one, the same way the remix rule worked
    - Words: remix, live, acoustic, unplugged, mix, instrumental, demo, session, extended, 12", orchestral, synthesis, dub, broadway, and rock/pop/country/spanish version
    - Only checks the Spotify title's suffix (after " - " or in brackets), so "Live Your Life" still matches
    - 74 rows moved to the studio recording (Mr. Brightside went from an 8.8 min club mix to 3.7 min); 10 rows with only an alternate recording are now unmatched
  - Notice: Spotify liveness and instrumentalness are unreliable per song (Holiday reads as live, Can't Get You Out of My Head as instrumental)
  - unicodedata - to strip accents, so Billboard and Spotify names match even when one has accents and the other doesn't

## Analysis Versions
  - v1: lexical diversity was unique ÷ total words, which drops as songs get longer
  - v2: switched lexical diversity to MTLD, removed scraping leftovers ("Contributors… Lyrics", ticket ads, "You might also like", "Embed"), and built 1–3 word n-grams within each line, dropping grams made only of stopwords
  - v3: also drops lines that are only a section header, e.g. "Verse 1:", "Chorus", "{Chorus}", "(Chorus 16X)", "-CHORUS-"

## Implementing Topics Analysis
- Uses Typesafe AI Jev SDK
- primary_probability, presence_probability, and analysis_version added to track_topics 
  - I'll want to keep track of main topics as well as partially covered topics

## Refactoring
- Add tests for service classes - minus transformers for now.
- Split Lyrics Cleaning into its own service to be used between lyrics analyzer and lyrics topic analyzer
- Split Lyrics Tokenizer into its own class

## Planning for Airflow
  - Planned DAG: run_etl -> analyze_lyrics -> plan_topic_batches -> analyze_topic batch

## Initial Exploratory Analysis
- Explicit lyrics nearly doubled. That happened within every genre, not just because hip-hop grew.
- Lifestyle & Success (money, status) grew the most of any theme. Love & Relationships and Sex & Desire declined.
- Love language is fading. Fewer songs use any "love" word, and they use them less often.
- The club disappeared from lyrics, along with "girl" and "move".
- Songs got shorter and sadder: about a minute shorter, lower valence and energy, more acoustic.
- Songs use fewer words but repeat less.

