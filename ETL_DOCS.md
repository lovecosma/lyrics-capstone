# ETL Documentation

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
