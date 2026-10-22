# Dashboard Documentation

## Views (sql/lyrics-views.sql)
The repositories query these views instead of the raw tables. They're created by the DAG's billboard_views task, right after the schema.


## chart_entry
- Inputs: chart_track, chart, track, track_genre, genre, broad_genre tables
- Purpose: 
  - One row per Hot 100 chart listing, with its year, rank, track and genre, as the base for most dashboard queries
- Interesting Parts: 
  - Genre tables are left-joined, so listings without a genre stay in with a NULL genre and broad_genre
  - is_explicit is the iTunes explicit flag 
- Key Tech:
  - Postgres view
- Outputs: 
  - chart_track_id, year, rank, track_id, title, artist_name, is_explicit, genre, broad_genre


## genre_theme_year_count
- Inputs: chart_entry view, lyrics_topic and topic tables
- Purpose: 
  - Count chart entries per year, broad genre and main topic, for the genre and topic charts
- Interesting Parts: 
  - Only joins each track's primary topic, so every entry is counted once
  - Keeps the topic analysis version as a column, so queries pick which version to count
  - Entries with no broad genre are kept as a NULL genre group
- Key Tech:
  - Postgres view
- Outputs: 
  - year, broad_genre, main_theme, topic_analysis_version, entry_count


## genre_track
- Inputs: chart_entry view
- Purpose: 
  - One row per track and broad genre
- Interesting Parts: 
  - Counts each song once, however many years it was on the chart
  - Leaves out tracks with no broad genre
- Key Tech:
  - Postgres view
- Outputs: 
  - track_id, broad_genre


## strong_profanity_word
- Inputs: profanity_word table
- Purpose: 
  - The list of strong profanity words, used to mask profanity in the dashboard's word lists
- Interesting Parts: 
  - Includes words rated Strong or Severe, and any word whose canonical form is one of six core words (fuck, shit, bitch, pussy, dick, ass)
- Key Tech:
  - Postgres view
- Outputs: 
  - word


## lyrics_word
- Inputs: lyrics_ngram_metric table, strong_profanity_word view
- Purpose: 
  - Each track's single words and how often they appear, flagged when they're strong profanity
- Interesting Parts: 
  - Keeps only 1-word n-grams
  - is_explicit here means the word is strong profanity
- Key Tech:
  - Postgres view
- Outputs: 
  - track_id, word, frequency, analysis_version, is_explicit


## track_topic
- Inputs: lyrics_topic and topic tables
- Purpose: 
  - Each track's topic results with topic names
- Interesting Parts: 
  - Has every topic for every track, not just the main one; filter on is_primary for the main topic or presence_probability for topics that are present
- Key Tech:
  - Postgres view
- Outputs: 
  - track_id, topic, is_primary, primary_probability, presence_probability, analysis_version


## Genre Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the genre data behind the Genre sheet and the Topic sheet's genre-by-topic heatmap
- Interesting Parts: 
  - get_year_counts counts chart entries per year and broad genre
  - get_topic_shares gives each genre's split of main topics, along with each topic's share across all genres, so the heatmap can show how far a genre is above or below average
  - Window functions get the genre, topic and overall totals in one pass instead of separate queries
  - Counts chart entries, not unique songs
  - Leaves out entries with no broad genre and only uses current analysis version.
  - analysis version and percent scale are passed as query parameters
- Key Tech:
  - pandas
  - Postgres window functions
  - CTEs 
    - since we're filtering on a window's result
- Outputs: 
  - get_year_counts: dataframe of year, broad_genre and entry_count
  - get_topic_shares: dataframe of broad_genre, main_topic, genre_song_count, genre_share and average_share (both shares are percentages)
