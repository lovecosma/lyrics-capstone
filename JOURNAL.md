# 10/13/2026

# Wrapping up planning 
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
  
# Feedback
  - Consider using Typesafe AI - https://typesafe.ai/blog/introducing-system-one-models-and-jev
  - Consider storing lyrics directly on track






