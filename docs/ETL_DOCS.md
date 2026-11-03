# ETL Documentation

## ETL DAG
Runs in this order:
  1. billboard_schema and billboard_views: create the tables and views from sql/
  2. etl: load tracks, topics, the emotion lexicon, profanity words and economic indicators, one after another, each in its own transaction
  3. lyrics_analysis: lyric metrics, then lyrics topics (snapshot, then live TypeSafe, then export the snapshot)
  4. genre_enrichment: iTunes genres (snapshot, then live iTunes search, then export the snapshot), then map genres to broad genres
- API results are restored from a CSV first, the live step only processes tracks the snapshot didn't cover, and the export adds new results back to the CSV
- Retrying a failed task is safe
- Each task opens its own engine from the billboard_postgres connection and disposes of it when done


## Extractor
- Inputs: DB Connection
- Purpose: 
  - Base extractor that reads CSVs, word lists and DB tables into the pipeline
- Interesting Parts: 
  - Passes any pandas read_csv options through, so subclasses and callers can tune parsing
  - Reads a batch of tracks by ID with one parameterized `any(:track_ids)` query
  - Reads word lists as a frozenset
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - Pandas dataframes, or a frozenset for word lists


## Billboard Extractor(Extractor)
- Inputs: DB Connection
- Purpose: provides basic extraction functionality from Extractor and adds functionality to extracts CSV dataframe from each each of 25 billboard year end chart listing
- Interesting Parts: 
  - Matches files on file name glob in given directory
  - Extract chart years from file names
- Key Tech:
  - pathlib (`Path.glob`) to find the yearly CSVs
  - pandas
  - re - regex for year extraction
- Outputs: 
  - Pandas dataframe with billboard chart listings


## NRC Lexicon Extractor(Extractor)
- Inputs: DB Connection
- Purpose: 
  - Read the tab-separated NRC lexicon file into a dataframe with the given column names
- Interesting Parts: 
  - The file has no header row, so callers pass the column names
  - Turns off quote handling, so words containing quote characters are read as-is
  - Only empty fields count as missing, so real words like "null" and "nan" aren't read as NaN
- Key Tech:
  - pandas
  - csv
- Outputs: 
  - Pandas dataframe of lexicon rows


## FRED Extractor(Extractor)
- Inputs: DB Connection
- Purpose: 
  - Read FRED series CSVs (one per indicator code) into a single long dataframe of observations
- Interesting Parts: 
  - Finds each file by indicator code (UNRATE → UNRATE.csv) in the given directory
  - Each FRED file names its value column after the code, so it's renamed to value and a code column is added before combining
  - Parses observation dates and reads FRED's "." as missing
- Key Tech:
  - pathlib
  - pandas
- Outputs: 
  - Pandas dataframe of observation_date, value and code for every series


## Loader
- Inputs: DB Connection
- Purpose: 
  - Write dataframes into the billboard_lyrics schema
- Interesting Parts: 
  - Three ways to write: append with, bulk insert with Postgres, or update existing rows by key
  - bulk inserts with COPY and updates use the raw psycopg connection under SQLAlchemy, for speed on large batches
  - COPY is used for the lyrics analysis results (lyrics_metric, lyrics_ngram_metric, lyrics_topic). They're written batch by batch and n-grams produce many rows per track, so streaming rows in one COPY is much faster than loading rows one by one
  - Converts missing values (NaN, NA) to None so they load as NULL
  - Builds table and column names with psycopg.sql identifiers, so names are quoted safely
- Key Tech:
  - pandas
  - SQLAlchemy connection
  - psycopg (COPY, executemany)
- Outputs: 
  - No returned output - writes data to the DB


## Track Processor
- Inputs: BillboardExtractor, Loader, Billboard directory path, Spotify CSV path
- Purpose: 
  - Orchestrate loading of tracks, charts, and chart tracks
  - merges Billboard chart listings with Spotify audio features 
- Interesting Parts: 
  - Matches Billboard rows to Spotify tracks by normalized track and artist names (TrackMerger)
  - Loads tracks before chart listings, then reads them back to get the database IDs that link them
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to DB


## Track Merger
- Inputs: Billboard dataframe, Spotify dataframe
- Purpose: 
  - Match each Billboard chart listing to its Spotify track to attach audio features
- Interesting Parts: 
  Steps following Billboard's 2003 "Crazy in Love" by "Beyonce":
    1. Normalize names: make both sources spell things the same
      - Lowercases, strips accents and punctuation, and collapses whitespace
      - Track names get several match spellings: without a "(feat. ...)" credit, without remaster/remix tags, without any bracketed or dashed suffix, and with trailing brackets stripped one at a time
      - Artist names keep only the primary artist (before "feat."), apply known aliases (Pink → P!nk), and drop a leading "the" and the word "and"
      - Also stores the lead artist, the first name in a credit like "Drake, Kanye West & Eminem"
      - Example: Billboard's "Beyonce" and Spotify's "Beyoncé" both become "beyonce", and Spotify's "Crazy In Love (feat. Jay-Z)" becomes "crazyinlove", same as Billboard's "Crazy in Love"
    2. Find candidates: merge Billboard and Spotify rows on any shared track spelling
      - Example: gives every Spotify "Crazy in Love", including covers by Emeli Sandé and SEVENTEEN and Beyoncé's live versions
    3. Match artists: keep only pairs where the artists agree
      - Exact (same full credit), lead artist (first name in a group credit), or featured (the Spotify artist starts the Billboard credit)
      - Example: "beyonce" = "beyonce" is an exact match; the covers are dropped
    4. Skip alternate versions: drop Live, Acoustic, Remix, etc. unless the Billboard title says the same
      - Keeps the audio features of the version that actually charted
      - Example: "Crazy In Love - Live" and "Crazy In Love - Homecoming Live" are dropped
    5. Pick the best candidate per Billboard row. Rank what's left and keep the top one
      - Exact artist → earliest year (usually the original) → no title suffix → most popular
      - Example: the 2003 "Crazy In Love (feat. Jay-Z)" wins
    6. Join back: left-join the winning Spotify columns (energy, tempo, ...) onto the Billboard rows by their original index
      - Songs with no match stay
      - Example: the Billboard row gets the 2003 recording's audio features, like tempo 99.165
- Key Tech:
  - unicodedata (NFKD) to strip accents
  - re patterns for punctuation, featured credits and version suffixes
  - pandas
- Outputs: 
  - Billboard dataframe with Spotify columns joined 


## Chart Transformer
- Inputs: merged track dataframe (from TrackMerger)
- Purpose: 
  - Build one chart row per Billboard year-end chart
- Interesting Parts: 
  - Takes the unique chart years from the track rows
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe with a single year column, ready to load into the chart table


## Track Transformer
- Inputs: merged track dataframe (from TrackMerger)
- Purpose: 
  - Build one track row per unique song (title + artist), with lyrics and Spotify audio features
- Interesting Parts: 
  - Songs that charted in several years are deduplicated, keeping the earliest year's row (stable sort, so ties keep their original order)
  - Renames track_name to title and keeps only the track table's columns
  - Casts key, mode, time_signature and duration_ms to nullable integers, so unmatched songs load as NULL instead of failing
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of unique tracks, ready to load into the track table


## ChartTrack Transformer
- Inputs: track and chart dataframes read back from the DB, merged track dataframe (from TrackMerger)
- Purpose: 
  - Link each track to every chart it appeared on, with its rank that year
- Interesting Parts: 
  - Matches DB tracks back to the source rows on title + artist to recover each chart year and rank
  - Swaps chart years for DB chart IDs, so the output only holds foreign keys and rank
  - A song that charted in several years gets one row per year
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of track_id, chart_id and rank, ready to load into the chart_track table


## TopicProcessor
- Inputs: Extractor, Loader, topics CSV path
- Purpose: 
  - Load the 10 lyric topics used for topic analysis into the DB
- Interesting Parts: 
  - Topics are hand-written in a CSV (name, display name, description), so they can change without code changes
  - TopicsTransformer keeps only the topic columns and drops duplicate names and incomplete rows
  - Descriptions are the criteria in the TypeSafe questions used by lyrics topic analysis
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the topic table


## Lookup Table Transformer
- Inputs: lookup dataframe (from a hand-written CSV)
- Purpose: 
  - Base transformer for small lookup tables like topics and economic indicators
- Interesting Parts: 
  - Subclasses only set three class attributes: KEY_COLUMN, COLUMNS and ROW_DESCRIPTION (used in the log line); they're declared as ClassVars with no defaults, so a subclass that forgets one fails with an AttributeError instead of silently using None
  - Keeps only COLUMNS, drops rows with a duplicate KEY_COLUMN, then drops incomplete rows
- Key Tech:
  - pandas
- Outputs: 
  - Cleaned dataframe, ready to load into its lookup table


## Topics Transformer(LookupTableTransformer)
- Inputs: topics dataframe (from topics CSV)
- Purpose: 
  - Clean the topics CSV into rows for the topic table
- Interesting Parts: 
  - All logic lives in LookupTableTransformer; TopicsTransformer only sets the key column (name), the columns to keep and a log label
  - Keeps only name, display_name and description, drops duplicate names, then drops incomplete rows
  - Shares its base class with EconomicIndicatorTransformer, so topics and economic indicators are cleaned the same way
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of topics, ready to load into the topic table


## Emotion Lexicon Processor
- Inputs: NrcLexiconExtractor, Loader, NRC emotion lexicon path
- Purpose: 
  - Load the NRC word-emotion lexicon so lyrics can be scored by emotion
- Interesting Parts: 
  - Keeps only word-emotion pairs the lexicon marks as associated (1), skipping the 0 rows
  - Adds dropped-g variants of "-ing" words ("loving" → "lovin"), since lyrics often spell them that way
  - Loads the emotions first, then reads them back to link each word to its emotion ID
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the emotion and word_emotion tables


## Emotion Lexicon Transformer
- Inputs: DroppedGVariantBuilder, NRC lexicon dataframe of word, emotion, association
- Purpose: 
  - Turn the raw NRC lexicon into one row per associated word and emotion
- Interesting Parts: 
  - Drops rows with no emotion and trims and lowercases words, so stray lines and spacing don't create bad pairs
  - Keeps only associated pairs
  - Adds dropped-g variants ("loving" → "lovin") from the injected variant builder, skipping any already in the lexicon
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of word and emotion name pairs, used to build the emotion and word_emotion tables


## Dropped G Variant Builder
- Inputs: lexicon dataframe, name of its word column, set of words already in the lexicon
- Purpose: 
  - Build "-in" spellings of "-ing" words so lexicon words match how lyrics are written ("loving" → "lovin")
- Interesting Parts: 
  - Lyrics tokenizing turns "lovin'" into "lovin", so without these variants those words would never match
  - Skips short words like "king" and "sing" whose stem is under 2 letters, since they aren't gerunds
  - Skips variants already in the lexicon, so a real entry is never duplicated or overridden
  - Copies the rest of each row (like the emotion), so the variant scores the same as the original word
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of new variant rows, same columns as the input, for the caller to append


## Emotion Transformer
- Inputs: word-emotion dataframe
- Purpose: 
  - Build one row per emotion for the emotion table
- Interesting Parts: 
  - Takes the unique emotion names from the word-emotion pairs, so the table always matches the lexicon
  - Sorts names alphabetically, so emotion IDs come out the same on every run
  - Adds a display name by title-casing the name ("anticipation" → "Anticipation")
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of name and display_name, ready to load into the emotion table


## Word Emotion Transformer
- Inputs: emotion dataframe read back from the DB, word-emotion dataframe (from EmotionLexiconTransformer)
- Purpose: 
  - Link each lexicon word to its emotions by emotion ID
- Interesting Parts: 
  - Joins on emotion name to swap names for the DB emotion IDs, so the output only holds the word and a foreign key
  - Inner join, so a pair whose emotion isn't in the DB is dropped instead of loading without an ID
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of word and emotion_id, ready to load into the word_emotion table


## Profanity Processor
- Inputs: Extractor, Loader, profanity CSV path
- Purpose: 
  - Load the profanity word list (with categories and severity ratings) that the strong_profanity_word view uses to find and mask strong profanity in lyric n-grams
- Interesting Parts: 
  - ProfanityWordTransformer lowercases and trims words but keeps punctuation, so spellings like "a_s_s" don't merge into ordinary words
  - Keeps only the first category and drops duplicate words
  - Skips words already in the table, so it's safe to re-run
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the profanity_word table


## Profanity Word Transformer
- Inputs: profanity dataframe (from the profanity CSV)
- Purpose: 
  - Clean the profanity CSV into rows for the profanity_word table
- Interesting Parts: 
  - Renames text to word and category_1 to category; category_2 and category_3 are dropped
  - Lowercases and trims words but keeps punctuation
  - Drops rows with no word and duplicates
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of word, canonical forms, category and severity, ready to load into the profanity_word table


## Economic Indicator Processor
- Inputs: FredExtractor, Loader, economic indicators CSV path, FRED directory path
- Purpose: 
  - Load economic indicators (unemployment, consumer sentiment, birth rate) and their FRED observations, to compare lyric trends against the economy
- Interesting Parts: 
  - The indicators CSV drives which FRED files are read: each indicator's code names its series file (UNRATE → fred/UNRATE.csv)
  - Loads indicators first, then reads them back to link each observation to its indicator ID
  - Drops observations FRED marks as missing (".")
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the economic_indicator and economic_observation tables


## Economic Observation Transformer
- Inputs: economic indicator dataframe read back from the DB, observation dataframe (from FredExtractor)
- Purpose: 
  - Link each FRED observation to its economic indicator by ID
- Interesting Parts: 
  - Drops observations with no value (FRED's "." for missing)
  - Joins on indicator code to replace codes for the DB indicator IDs, so the output only holds a foreign key, date and value
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of economic_indicator_id, observation_date and value, ready to load into the economic_observation table


## Economic Indicator Transformer(LookupTableTransformer)
- Inputs: economic indicators dataframe (from economic indicators CSV)
- Purpose: 
  - Clean the economic indicators CSV into rows for the economic_indicator table
- Interesting Parts: 
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of economic indicators, ready to load into the economic_indicator table


## Batching (run_in_batches)
- Inputs: DB connection, Extractor, a batch processor (TrackBatchProcessor), batch size
- Purpose: 
  - Run long track-by-track work (lyric metrics, topics, genres) in batches, so a failure only loses the batch in progress
- Interesting Parts: 
  - A batch processor has three methods (TrackBatchProcessor protocol): select_pending, compute_batch and load_batch
  - Plans every batch up front: select_pending runs once, and its track IDs are split into batches
  - For each batch: read the tracks in one transaction, compute outside any transaction (so slow API calls don't hold one open), then write and commit in another
  - Committed batches are skipped on the next run by select_pending, so a failed run picks up where it stopped
  - Key Tech:
  - itertools.batched
  - SQLAlchemy connection
- Outputs: 
  - No returned output - each processor loads its own data


## Lyrics Analysis Processor
- Inputs: Extractor, Loader, LyricsAnalyzer
- Purpose: 
  - Compute lyric metrics (word count, unique words, lexical diversity, average word length) and n-gram frequencies for each track
- Interesting Parts: 
  - Built to run in batches. Selects pending tracks to analyze, compute_batch analyzes one batch, load_batch writes it, and each batch commits on its own
  - Skips tracks already analyzed with the current analysis version
  - Writes results with COPY, because n-grams produce many rows per track
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the lyrics_metric and lyrics_ngram_metric tables


## Lyrics Analyzer
- Inputs: non-content word set (stopwords, lyric stopwords and filler words), track dataframe (track_id, lyrics)
- Purpose: 
  - Turn each track's raw lyrics into one row of word metrics and many rows of n-gram frequencies
- Interesting Parts: 
  Steps following Billboard's 2003 "Crazy in Love" by "Beyonce":
    1. Skip analyzed tracks: select_unanalyzed drops tracks that already have a lyrics_metric row for the current ANALYSIS_VERSION
    2. Clean: LyricsCleaner removes scrape artifacts and section headers
      - Artifacts: "3 ContributorsHello Lyrics", "See Adele LiveGet tickets as low as $45", "You might also like", trailing "Embed"
      - Section headers in brackets, dashes or bare: [Chorus], (Verse 2), -CHORUS-, Hook x2, [Verse 1: Drake]
    3. Tokenize: LyricsTokenizer splits lyrics into lines of lowercase words
      - Curly apostrophes become straight ones and zero-width spaces are removed
      - Keeps apostrophes inside words but drops them at the ends, and splits on hyphens and underscores
      - Empty lines are dropped, and lines are kept so n-grams don't cross line breaks
      - Example: "When you leave, I'm beggin' you not to go" → when, you, leave, i'm, beggin, you, not, to, go; "Uh-oh, uh-oh" → uh, oh, uh, oh
    4. Compute word metrics: one lyrics_metric row per track
      - word_count and unique_word_count
      - lexical_diversity is MTLD (lexicalrichness), which unlike a plain unique/total ratio doesn't drop just because a song is longer
        - MTLD reads the words in order and tracks the share of unique words seen so far. The score is the total word count divided by the number of segments. It's the average run of words before the song starts repeating itself. 
    5. Count n-grams: every 1-, 2- and 3-word sequence within a line, with its frequency in the song
      - Example: "Got me looking so crazy right now" gives got, got me, got me looking, me, me looking, me looking so, ...
    6. Drop non-content n-grams: an n-gram is kept unless every word in it is a non-content word
      - Example: "uh oh" (37 times) and "oh" (54) are dropped, but "so crazy" (31) stays because "crazy" is content; 184 of 922 n-grams are dropped
      - Example: the top n-grams kept are "got" (41), "got me" (39) and "crazy" (34)
- Key Tech:
  - re patterns for scrape artifacts and section headers
  - nltk (RegexpTokenizer, everygrams, FreqDist)
    - RegexpTokenizer splits text into tokens by returning every match of a regex. Here the pattern grabs runs of letters and digits
    - everygrams returns every run of consecutive words in a sequence with a length from a minimum to a maximum
    - FreqDist counts how many times each item appears. Passing it the n-grams gives each one's frequency in the song
  - lexicalrichness (MTLD)
  - pandas
- Outputs: 
  - lyrics_metric dataframe: track_id, word_count, unique_word_count, lexical_diversity, average_word_length, analysis_version
  - lyrics_ngram_metric dataframe: track_id, ngram, n, frequency, analysis_version


## Lyrics Cleaner
- Inputs: raw lyrics string
- Purpose: 
  - Scrape artifacts and section headers (as much as possible :/) so they aren't counted as lyrics
  - Shared by LyricsAnalyzer and LyricsTopicAnalyzer
- Interesting Parts: 
  - Artifacts are replaced with a line break, so lyrics on either side don't join into one line and a header stuck to an artifact ends up on its own line
  - Then removes section headers in brackets, dashes or bare
  - Headers are only removed when they're alone on a line, so a lyric like "Sing the chorus" stays
  - The header pattern is built from small named regex patterns
- Key Tech:
  - re
- Outputs: 
  - Cleaned lyrics string, with line breaks kept for tokenizing


## Lyrics Tokenizer
- Inputs: cleaned lyrics string (from LyricsCleaner)
- Purpose: 
  - Split lyrics into lines of lowercase words for LyricsAnalyzer's word metrics and n-grams
- Interesting Parts: 
  - Turns curly apostrophes into straight ones and removes zero-width spaces, so "don’t" and "don't" count as the same word
  - Uses casefold, so "Straße" and "STRASSE" both become "strasse"
  - A word is a run of letters or digits, and apostrophes are kept inside it: "rock'n'roll" stays one word, "lovin'" becomes "lovin"
  - Hyphens, underscores and other punctuation split words: "Uh-oh" → uh, oh; "rock'n'roll_2am" → rock'n'roll, 2am
  - Accented letters count as letters, so "café" stays whole
  - Keeps one list per line and drops empty lines
- Key Tech:
  - nltk RegexpTokenizer
- Outputs: 
  - List of lines, each a list of words


## Topic Analyzer
- Inputs: topic dataframe (from the topic table)
- Purpose: 
  - Base class for the snapshot and TypeSafe topic analyzers
- Interesting Parts: 
  - Holds ANALYSIS_VERSION, which is shared by both analyzers so restored and live results count as the same version
  - Builds the topic name to topic ID lookup
  - select_uncategorized skips tracks that already have topics for the current version
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of tracks that still need topics


## Snapshot Lyrics Topic Analyzer(TopicAnalyzer)
- Inputs: topic dataframe (from the topic table), snapshot dataframe (from typesafe_lyrics_topics.csv), track dataframe
- Purpose: 
  - Restore TypeSafe topic results from a saved CSV snapshot instead of calling the API again
- Interesting Parts: 
  - Matches snapshot rows to tracks by title and artist name
  - Only uses snapshot rows for the current ANALYSIS_VERSION
  - Maps topic names back to the topic table's IDs and drops any topic that's no longer in the table
  - skip tracks already categorized
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of track_id, topic_id, is_primary, primary_probability, presence_probability, model_version and analysis_version, ready to load into the lyrics_topic table


## Lyrics Topic Processor
- Inputs: Extractor, Loader, topic analyzer (SnapshotLyricsTopicAnalyzer or LyricsTopicAnalyzer)
- Purpose: 
  - Categorize each track's lyrics into topics, with primary and presence probabilities
- Interesting Parts: 
  - Built to run in batches. Selects pending tracks to categorize, compute_batch categorizes one batch, load_batch writes it, and each batch commits on its own
  - Skips tracks already categorized with the current analysis version
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the lyrics_topic table


## Lyrics Topic Analyzer(TopicAnalyzer)
- Inputs: topic dataframe (from the topic table), TypeSafe client factory, track dataframe
- Purpose: 
  - Categorize each track's lyrics into topics with the TypeSafe API
- Interesting Parts: 
  - Asks every question in one request per track: a Choice for the main topic, plus a Noul (yes/no probability) for each topic's presence
  - The topic descriptions from the topic table are the Choice options and the Noul themes, so changing topics.csv changes the questions
  - Writes one row per topic per track: is_primary, the main-topic probability, and the presence probability
  - A failed request logs a warning and skips the track, so it's retried on the next run
- Key Tech:
  - TypeSafe SDK (async client, Choice, Noul)
  - asyncio
  - pandas
- Outputs: 
  - Dataframe of track_id, topic_id, is_primary, primary_probability, presence_probability, model_version and analysis_version, ready to load into the lyrics_topic table


## Lyrics Topic Snapshot Processor
- Inputs: Extractor, Loader, snapshot CSV path (typesafe_lyrics_topics.csv)
- Purpose: 
  - Save the lyrics_topic results to a CSV snapshot so SnapshotLyricsTopicAnalyzer can restore them after a database rebuild instead of calling TypeSafe again
- Interesting Parts: 
  - Uses artist name and topic name for ID since actual IDs change when the database is rebuilt
  - new rows are appended to the existing CSV
  - Duplicates are keyed by title, artist, topic and analysis version, so results from older versions are kept alongside new ones
  - Loader writes to a temp file and then replaces the CSV, so a crash never leaves a half-written snapshot
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - writes the merged snapshot to typesafe_lyrics_topics.csv


## Genre Enrichment Processor
- Inputs: Extractor, Loader, genre enricher (SnapshotGenreEnricher or TrackGenreEnricher)
- Purpose: 
  - Give each track an iTunes genre and explicit flag
- Interesting Parts: 
  - Built to run in batches. Selects pending tracks, compute_batch enriches one batch, load_batch writes it, and each batch commits on its own
  - Skips tracks that already have a genre or were already searched (genre_searched_at)
  - Loads only genres not already in the genre table, links tracks to them, then updates is_explicit and genre_searched_at on the track table
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the genre and track_genre tables and updates the track table


## Genre Enricher
- Inputs: track dataframe, track_genre dataframe, genre dataframe
- Purpose: 
  - Shared selection logic for the snapshot and iTunes enrichers
- Interesting Parts: 
  - select_missing picks tracks with no genre that haven't been searched
  - select_new_genres keeps only genres not already in the genre table
  - select_explicit keeps tracks whose explicit flag is known
- Key Tech:
  - pandas
- Outputs: 
  - Dataframes of tracks or genres to load


## Snapshot Genre Enricher(GenreEnricher)
- Inputs: snapshot dataframe (from itunes_track_genres.csv), track dataframe
- Purpose: 
  - Restore iTunes genres from a saved CSV snapshot instead of searching again
- Interesting Parts: 
  - Matches snapshot rows to tracks by title and artist name
- Key Tech:
  - pandas
- Outputs: 
  - GenreSearchResult: tracks with a genre, and tracks that were searched


## Track Genre Enricher(GenreEnricher)
- Inputs: iTunes client factory, track dataframe
- Purpose: 
  - Search iTunes for each track and take the genre and explicit flag of the best matching song
- Interesting Parts: 
  - Searches by title and primary artist (without "feat." credits)
  - Reuses TrackMerger to pick the best result, with the release year as the candidate year and earlier search results ranked as more popular
  - iTunes "cleaned" (the edited version of an explicit song) counts as explicit
- Key Tech:
  - TrackMerger
  - pandas
- Outputs: 
  - GenreSearchResult: tracks with a genre, and tracks that were searched


## iTunes Client
- Inputs: optional requests session
- Purpose: 
  - Search the iTunes Search API for songs
- Interesting Parts: 
  - Waits at least 3 seconds between requests
  - Retries throttled requests with exponential backoff, up to 3 attempts
  - The rate limit is per client, so the DAG's search task allows only one running instance
- Key Tech:
  - requests
- Outputs: 
  - List of iTunes song results


## Genre Snapshot Processor
- Inputs: Extractor, Loader, snapshot CSV path (itunes_track_genres.csv)
- Purpose: 
  - Save track genres to a CSV snapshot so SnapshotGenreEnricher can restore them
  - Uses title and artist name instead
  - Keeps searched tracks with no match, so they aren't searched again
  - New rows are appended to the existing CSV
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - writes the merged snapshot to itunes_track_genres.csv

## Genre Mapping Processor
- Inputs: Extractor, Loader, genre mapping CSV path (genre_mapping.csv)
- Purpose: 
  - Group iTunes genres into broad genres (Pop, Hip-Hop/Rap, ...) for analysis
- Interesting Parts: 
  - Loads only broad genres not already in the table
  - Sets broad_genre_id on each genre by name
  - logs any genre with no mapping
- Key Tech:
  - pandas
  - SQLAlchemy connection
- Outputs: 
  - No returned output - loads data to the broad_genre table and updates the genre table


## Genre Transformer
- Inputs: source track dataframe (from a genre enricher)
- Purpose: 
  - Build the unique genre names for the genre table
- Interesting Parts: 
  - Trims and lowercases genre names, so iTunes' "Hip-Hop/Rap" is stored as "hip-hop/rap"
  - Drops missing and duplicate genres
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of genre names, ready to load into the genre table


## Track Genre Transformer
- Inputs: track dataframe from the DB, genre dataframe read back from the DB, source track dataframe (from a genre enricher)
- Purpose: 
  - Link each track to its genre by ID
- Interesting Parts: 
  - Matches source rows to tracks by title and artist name
  - Normalizes genre names the same way as GenreTransformer, then joins on name to get the genre IDs from the DB
  - Tracks with no genre are dropped, and duplicate links are removed
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of track_id and genre_id, ready to load into the track_genre table


## Broad Genre Transformer
- Inputs: genre mapping dataframe (from genre_mapping.csv)
- Purpose: 
  - Build the unique broad genre names for the broad_genre table
- Interesting Parts: 
  - Drops missing and duplicate broad genres
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of broad genre names, ready to load into the broad_genre table


## Genre Mapping Transformer
- Inputs: genre dataframe read back from the DB, broad genre dataframe read back from the DB, genre mapping dataframe (from genre_mapping.csv)
- Purpose: 
  - Pair each genre's ID with its broad genre's ID
- Interesting Parts: 
  - Normalizes the CSV's genre names the same way as GenreTransformer, so they match the names in the DB
  - Joins genre → mapping → broad genre to swap names for IDs
- Key Tech:
  - pandas
- Outputs: 
  - Dataframe of genre_id and broad_genre_id, used to update the genre table


