# Dashboard Documentation

## App (app.py)
- Inputs: DB_ENGINE_URL from .env 
- Purpose: 
  - Start the Dash app: load every sheet's data from the repositories, build the layout and serve it
- Interesting Parts: 
  - The topic distinctive terms query is passed the main topics from TopicRepository, so it scores the same topics the other topic charts show
  - Genre and topic colors are worked out once from the genre and topic counts and passed to both the layout and the callbacks, so a genre or topic is the same color on every sheet
  - callbacks.set_data hands the callbacks the dataframes behind the vocabulary and word trend pickers, so changing a picker redraws its chart without querying the database
  - Changes into the dashboard folder on startup, so Dynaconf finds .env
- Key Tech:
  - Dash
  - SQLAlchemy
  - Dynaconf

## Callbacks (callbacks.py)
- Inputs: genre and topic distinctive terms, genre and topic colors, and word year counts, passed in by app.py through set_data
- Purpose: 
  - Redraw the Vocabulary sheet's four picker charts when a picker changes
- Interesting Parts: 
  - update_genre_vocabulary_chart / update_topic_vocabulary_chart show the picked genre's or topic's distinctive terms against every other genre or topic, in the picked one's color
  - update_genre_word_change_chart / update_topic_word_change_chart show which words gained or lost the most between the early and late chart years for the picked genre or topic. The "All genres" and "All songs" options use every entry
  - The callbacks register with Dash when app.py imports the module, before any data is loaded, so set_data stores the data in module globals for them to read later
  - prevent_initial_call skips the first run, since the layout already draws each chart's starting figure
- Key Tech:
  - Dash callbacks
  - pandas
- Outputs: 
  - A new Plotly figure for the chart tied to the picker

## Layout (layout.py)
- Inputs: the dataframes app.py loads from the repositories
- Purpose: 
  - Build the whole page
- Sheets: 
  - Genre: genre share line chart and period table
  - Topic: animated main topic vs. topic mentioned bubble chart, period table and genre-by-topic heatmap
  - Vocabulary: "By genre" and "By topic" tabs, each with a distinctive terms chart and a word change chart, both with pickers
  - Explicit: explicit words per 1,000 words by year, plus "By genre" and "By topic" tabs with breakdown charts and tables
  - Emotion: emotion share chart and period table
  - Sound: song length and audio feature charts, and a sound table
  - Economy: unemployment vs. Party & Celebration share chart
- Interesting Parts: 
  - Shared helpers keep the sheets consistent:
    - yearly_shares turns year counts into each year's % of entries, for the genre share chart, the topic bubble chart and the Economy sheet's party share
    - build_share_table shows each genre, topic or emotion's share in each period and the change from first to last, for the Genre, Topic and Emotion sheets
    - comparison_periods splits the years into early, middle and late periods (the first and last 8 years and the years between) for the period tables and word change charts
    - category_order sorts genres or topics by total entries, and category_colors gives each one a fixed color in that order, so colors match across sheets
    - change_class marks a change in the tables as up or down when it's past a "flat" threshold, and muted otherwise (colors are in style.css)
    - build_chart_title and the chart font constants give every chart the same title style
    - build_chart_note and the *_SOURCE dicts add the source note under each sheet
  - main_topics picks the 7 topics with the most entries (MAIN_TOPIC_COUNT); app.py also uses it to choose which topics to score for distinctive terms
  - The Economy chart standardizes both lines (z-scores), so unemployment and party share can be compared on one axis
  - Each sheet's write-up quotes specific numbers (e.g. "+13.0 points").
  - The chart and picker IDs are constants, so callbacks.py and the layout refer to the same components
  - Styles come from assets/style.css, which Dash loads automatically
- Key Tech:
  - Dash html and dcc components
  - Plotly Express and Graph Objects
  - pandas
- Outputs: 
  - build_layout: the Dash component tree that app.py sets as app.layout

## Views 
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


## track_explicit
- Inputs: lyrics_word view
- Purpose: 
  - Each track's word count and strong profanity count, for the explicit language queries and the "[strong profanity]" distinctive term
- Interesting Parts: 
  - Rolls up lyrics_word once per track and analysis version, so the explicit queries just join it to chart_entry
  - Tracks with no strong profanity get an explicit_word_count of 0 instead of NULL
- Key Tech:
  - Postgres view
  - Postgres filter clauses and bool_or
- Outputs: 
  - track_id, analysis_version, word_count, explicit_word_count, has_explicit


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


## Topic Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the topic data behind the Topic sheet
- Interesting Parts: 
  - get_year_counts counts chart entries per year and main topic. It sums genre_theme_year_count across genres, so entries with no broad genre are still counted
  - get_presence_year_counts counts chart entries per year for each topic that's present in a song: its main topic, or any topic with a presence probability of at least 0.7
  - Counts chart entries, not unique songs
  - analysis version and presence threshold are passed as query parameters
- Key Tech:
  - pandas
- Outputs: 
  - get_year_counts: dataframe of year, main_topic and entry_count
  - get_presence_year_counts: dataframe of year, topic and entry_count


## Vocabulary Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - query the word data behind the vocabulary sheet 
  - distinctive terms, word trends and words every genre shares
- Interesting Parts: 
  - get_genre_distinctive_terms and get_topic_distinctive_terms share one query (_get_distinctive_terms) and only pass in a different category_track SQL, so genres and main topics are scored the same way
    - A term's category_share is the % of the category's songs that use it; other_share is the % of every other category's songs that use it
    - Terms are ranked by lift (category_share / (other_share + 0.5)). The 0.5 smoothing keeps terms that are rare everywhere else from jumping to the top
    - Terms need to be in at least 8% of the category's songs, and the top 10 per category are kept
    - Words and 2-word phrases containing strong profanity are left out and grouped into one "[strong profanity]" term. That term is only shown when the category uses it more than the other categories do
  - get_word_year_counts counts chart entries using each word per year, broad genre and main topic, along with that group's total entries, so word trends can be shown as shares
    - Only keeps words used in at least 100 entries across all years (MIN_WORD_ENTRY_COUNT)
    - Strong profanity words are grouped into "[strong profanity]"
    - Entries with no genre or topic are kept
  - get_shared_top_words returns the words in the top 12 of every vocabulary genre (SHARED_WORD_RANK), ordered by average share
  - Distinctive and shared terms count unique songs; word trends count chart entries
  - Analysis versions, thresholds and the profanity label are passed as query parameters
- Key Tech:
  - pandas
  - Postgres window functions
  - CTEs
    - to filter on a window's result and to reuse one intermediate result in several steps
- Outputs: 
  - get_genre_distinctive_terms / get_topic_distinctive_terms: dataframe of category, ngram, category_share and other_share
  - get_word_year_counts: dataframe of year, broad_genre, main_topic, word, entry_count and year_entry_count
  - get_shared_top_words: list of words


## Explicit Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the explicit language data behind the Explicit sheet
- Interesting Parts: 
  - get_year_rates gives two yearly measures: strong profanity words per 1,000 words, and the % of chart entries with at least one
  - get_breakdown_counts counts explicit and total chart entries per year, broad genre and main topic, so the dashboard can filter and regroup them without another query
  - Both read per-track counts from the track_explicit view, so neither needs its own per-song rollup
- Key Tech:
  - pandas
  - Postgres filter clauses
- Outputs: 
  - get_year_rates: dataframe of year, explicit_rate and explicit_song_share
  - get_breakdown_counts: dataframe of year, broad_genre, main_topic, explicit_entry_count and entry_count


## Emotion Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the emotion data behind the Emotion sheet
- Interesting Parts: 
  - get_year_shares gives the % of each year's lyric words that carry each NRC emotion
  - Counts word occurrences (frequency)
  - Strong profanity words are left out of both the emotion counts and the year's total
  - The year's total includes words with no emotion
  - Analysis version and percent scale are passed as query parameters
- Key Tech:
  - pandas
  - CTEs
    - to total each year's words once before joining the lexicon
- Outputs: 
  - get_year_shares: dataframe of year, emotion, word_count, year_word_count and word_share


## Economy Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the economic data behind the Economy sheet
- Interesting Parts: 
  - get_year_averages averages each FRED indicator's observations by calendar year
  - Returns every indicator over every year it has data. I filter  which data to use on frontend.
- Key Tech:
  - pandas
- Outputs: 
  - get_year_averages: dataframe of indicator, year and value


## Sound Repository
- Inputs: SQLAlchemy engine
- Purpose: 
  - Query the Spotify audio data behind the Sound sheet
- Interesting Parts: 
  - get_year_averages averages each year's song length (in minutes) and Spotify audio features: valence, energy, danceability, acousticness and speechiness
  - matched_share is the % of each year's entries that have Spotify data; the song length chart shows it on hover
  - Stops at 2022
  - Counts chart entries, not unique songs
  - Percent scale, ms-per-minute and the last year are passed as query parameters
- Key Tech:
  - pandas
- Outputs: 
  - get_year_averages: dataframe of year, matched_share, minutes, valence, energy, danceability, acousticness and speechiness