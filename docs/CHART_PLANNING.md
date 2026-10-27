# Chart Planning

Findings for the dashboard, checked against the hypotheses in [PLANNING.md](PLANNING.md). Every chart uses data already in the `billboard_lyrics` schema.

## Data and conventions

- 2,484 chart entries (2,247 unique tracks), 25 year-end charts, 98–100 entries per year.
- Chart positions come from the Billboard Year-End Hot 100 (Billboard, 2000–2024). Lyrics come from a dataset compiled from those charts and the Genius API (Melo, 2026a, 2026b).
- Genres and explicit flags come from the iTunes Search API (Apple Inc., 2026). Genres are grouped into broad genres using `data/genre_mapping.csv`.
- Audio features, including duration, come from a Spotify tracks dataset (Joshi, 2023).
- Topics are main topics from `lyrics_topic` (analysis `v1`), classified by TypeSafe's Jev model (TypeSafe, 2026). Lyric metrics and n-grams are from analysis `v3`.
- **Periods:** early is 2000–07, mid is 2008–16, late is 2017–24.
- **Trends** are straight-line fits through the 25 yearly values, quoted as fitted 2000 → 2024 values with r and p.
- **Genre mix:** a late-period rate "at the early genre mix" weights each genre's late rate by how common that genre was in 2000–07. It shows what the late number would be if the genre mix hadn't changed.
- In the planning hypotheses, "Dance" means the **Pop** broad genre.

## Hypotheses vs. results

| Hypothesis | Result |
|---|---|
| The number of explicit hits went up | **Confirmed**: 24% → 43% of entries |
| Heartbreak & Loss has always been the top topic | **Rejected**: Love was #1 in 17 of 25 years. Heartbreak was #1 only in 2024. |
| Songs about Self-Reflection & Growth went down | **Weakly confirmed** (r = −0.41, p = 0.044), but the change in genre mix explains all of it |
| Most songs are not about Self-Reflection & Growth | **Confirmed**: 7% of entries |
| Love & Relationships is R&B's top topic | **Confirmed**: 34%, with Sex & Desire close behind at 23% |
| Pop emphasizes Party and Lifestyle | **Rejected**: Pop is 30% Love and 21% Heartbreak, versus 9% Party and 3% Lifestyle |
| Pop shifts from Heartbreak toward Party | **Rejected, the reverse happened**: Heartbreak rose (16% → 26%, r = 0.40, p = 0.05). Party has no trend; it spiked in 2010–11. |
| Topic changes are partly explained by genre popularity | **Confirmed, and it differs by topic**: see finding 5 |
| Vocabulary and common phrases changed | **Confirmed**: see finding 7 |
| Words and phrases differ across genres and topics | **Confirmed for distinctive words**. The most frequent words are the same everywhere. See finding 9. |

## Findings

### 1. Country took over the 2020s while R&B and rock faded

| Genre | 2000–07 entries | 2017–24 entries |
|---|---|---|
| Country/Folk | 47 | 145 |
| R&B/Soul | 166 | 49 |
| Rock/Alternative | 121 | 41 |

Findings 4 and 5 depend on this shift.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Genre share by year | Multi-line chart | Year | % of entries; one line per genre | `chart_entry` (built in the dashboard) |

### 2. Explicit hits nearly doubled, inside every genre

- 24% of entries were explicit in 2000–07 and 43% in 2017–24 (r = 0.70). The peak was 52% in 2021.
- At the early genre mix, the late share would still be 44%, so hip-hop's growth doesn't explain the rise.
- R&B went from 11% to 55%, Pop from 8% to 29%, and Country from 0% to 8%.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Explicit share by year | Line chart | Year | % of entries flagged explicit | `chart_entry.is_explicit` |
| Explicit share by genre | Dumbbell or grouped bar chart | % explicit | Genre; 2000–07 vs. 2017–24 | `chart_entry` |

PLANNING.md planned a 100% stacked line here. With only explicit and clean, a single line is easier to read.

### 3. Love stayed on top, but the top 5 changed

| Rank | 2000–07 | 2017–24 |
|---|---|---|
| 1 | Love & Relationships 27% | Love & Relationships 23% |
| 2 | Sex & Desire 17% | Heartbreak & Loss 20% |
| 3 | Heartbreak & Loss 16% | **Lifestyle & Success 18%** |
| 4 | Empowerment & Confidence 11% | Sex & Desire 12% |
| 5 | Self-Reflection & Growth 9% | Empowerment & Confidence 10% |

- Biggest risers: Lifestyle & Success (5% → 18%, r = 0.58) and Heartbreak & Loss (13% → 21%, r = 0.52).
- Biggest declines: Love & Relationships (−9 points) and Self-Reflection & Growth (−3 points).
- Compare periods, not single years. Love alone swings from 41% in 2000 to 15% in 2024.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Top 5 topics, early vs. late | Grouped horizontal bar chart | % of entries | Topic; bars grouped by period | `genre_theme_year_count` |
| Biggest topic increases and decreases | Diverging bar chart | Point change, early → late | Topic | `genre_theme_year_count` |

### 4. Hip-hop became a genre about money and status

- Within hip-hop, Lifestyle & Success went from 20% to 34% to 52% across the three periods. Sex & Desire fell from 32% to 12%.
- Lifestyle & Success is at most 4% of every other genre with more than 30 entries.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Lifestyle & Success: hip-hop vs. other genres | Line chart | Year | % of entries; two lines | `genre_theme_year_count` |
| Hip-hop topics by period (optional) | 100% stacked bar chart | Period | % of hip-hop entries by topic | `genre_theme_year_count` |

### 5. Genre changes explain some topic shifts but not others

This answers the main proposal question: did the topics change, or did the genres on the charts change?

| Topic | 2000–07 | 2017–24 actual | 2017–24 at early genre mix | Reading |
|---|---|---|---|---|
| Self-Reflection & Growth | 8.8% | 6.5% | 9.3% | **Explained entirely by genre**: rock is 24% self-reflection, and rock shrank |
| Lifestyle & Success | 7.2% | 18.4% | 14.2% | **Partly genre** (about 4 of the 11 points), mostly hip-hop itself changing |
| Heartbreak & Loss | 16.3% | 20.3% | 22.2% | **Not genre**: grew within genres (Country 9% → 35%, Pop 20% → 25%) |
| Sex & Desire | 17.3% | 12.2% | 12.5% | **Not genre**: the decline happened within hip-hop |

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Actual vs. genre-mix-adjusted topic share | Grouped bar chart | Topic | % of entries; bars for 2000–07, 2017–24 actual, 2017–24 at early genre mix | `genre_theme_year_count` |
| Heartbreak within each genre | Small multiples (one panel per genre) | Period | % of the genre's entries | `genre_theme_year_count` |

### 6. Each genre emphasizes different topics

- Love leads in Country (39%), Dance/Electronic (37%), R&B (34%) and Pop (30%).
- Hip-hop is led by Lifestyle & Success (37%) and Rock by Self-Reflection & Growth (24%).
- In Pop, Party was a spike, not a trend: 20% in 2010 and 36% in 2011, then back to single digits. Heartbreak rose steadily.

| Pop topic | 2000–07 | 2008–16 | 2017–24 |
|---|---|---|---|
| Heartbreak & Loss | 19.8% | 19.2% | 24.5% |
| Party & Celebration | 5.8% | 12.9% | 4.6% |

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Topics by genre | Heatmap | Topic | Genre; color: % of the genre's entries | `genre_theme_year_count` |
| Party vs. Heartbreak within Pop | Line chart | Year | % of Pop entries; two lines | `genre_theme_year_count` |

Pop has only 22–47 entries a year. Show the yearly counts or the period averages on the Pop chart so the 2010–11 spike doesn't read as a trend.

### 7. Love and the club faded, profanity and rap slang rose

Share of songs using each word:

| Word | 2000–07 | 2017–24 |
|---|---|---|
| girl | 43% | 28% |
| love | 57% | 46% |
| club | 15% | 5% |
| world | 21% | 13% |
| tryna | 11% | 21% |
| lil | 8% | 14% |

Strong profanity (f-words, "shit", "bitch") rose by 11–14 points.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Biggest word gains and losses | Diverging bar chart | Point change in % of songs | Word | `lyrics_ngram_metric` |
| Chosen words over time | Multi-line chart | Year | % of songs using the word | `lyrics_ngram_metric` |

"Love" falls in both the vocabulary and the topics, which links this finding to finding 3.

### 8. Songs got shorter and use fewer words, but vocabulary variety barely changed

| Measure | Fitted 2000 | Fitted 2024 | r | p |
|---|---|---|---|---|
| Duration | 4.3 min | 3.3 min | −0.93 | < 0.001 |
| Word count | 530 | 422 | −0.72 | < 0.001 |
| Lexical diversity (MTLD) | 32 | 37 | +0.32 | 0.12 (not significant) |

- Duration is the strongest trend in the data.
- TRENDS.md says recent songs repeat less. The MTLD rise isn't significant, so that claim is too strong.
- By genre, Country has the most varied vocabulary (median MTLD 47) and Dance/Electronic the least (22).

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Word count and duration by year | Multi-line chart (two y-axes) | Year | Average word count; average minutes | `lyrics_metric`, `track.duration_ms` |
| Vocabulary diversity by genre | Box plot | Genre | MTLD | `lyrics_metric` |

### 9. Each genre and topic has its own vocabulary on top of a shared core

The **most frequent** words are almost the same in every genre and topic: "know", "like", "got", "get", "love" and "baby", and phrases like "I know", "you know" and "I can't". A most-frequent chart would show identical bars for every group.

The **distinctive** words differ sharply. These are words used in at least 8% of a group's songs, ranked by how much more common they are there than in all other songs. Figures are the share of songs using the word, in the group vs. everywhere else.

| Genre | Distinctive words and phrases |
|---|---|
| Country/Folk | truck 12% vs 1%, whiskey 11% vs 1%, town 20% vs 5%, road 16% vs 4%, "a little" 25% vs 10% |
| R&B/Soul | babe 17% vs 5%, ladies, body 21% vs 9%, "girl I" 21% vs 5%, "without you" |
| Pop | heart 28% vs 17%, tonight 18% vs 11%, "my heart" 16% vs 8% (only mildly distinctive) |
| Rock/Alternative | world 26% vs 16%, dream(s), soul, "my head", "the world" |
| Hip-Hop/Rap | profanity and slurs (about 45% vs 3–4%), skrrt, "this shit", "pull up" |

| Topic | Distinctive words and phrases |
|---|---|
| Party & Celebration | party 41% vs 5%, dj, dance floor, "in the club" 21% vs 4%, "hands up", "turn it up" |
| Lifestyle & Success | rich 24% vs 2%, racks, wrist, gang, trap, "pull up" |
| Heartbreak & Loss | gone, goodbye, tears, broken, hurt, "used to", "you said", "I wish" |
| Love & Relationships | forever, kiss, together, "love you" 19% vs 6%, "your eyes" |
| Sex & Desire | body 31% vs 8%, hips, taste, "your body", "you want it" |
| Self-Reflection & Growth | pain, dreams, afraid, "my mind", "one day", "to find" |

The topic words match each topic's meaning, which is evidence the model labelled songs sensibly. Present the topic chart as a check on the topic labels.

| Chart | Type | X-axis | Y-axis / encoding | Source |
|---|---|---|---|---|
| Distinctive words by genre | Horizontal bar chart with a genre dropdown | % of songs | Word; bars for the genre vs. all other songs | `lyrics_ngram_metric` |
| Distinctive words by topic | Horizontal bar chart with a topic dropdown | % of songs | Word; bars for the topic vs. all other songs | `lyrics_ngram_metric` |

Open the genre chart on Country: truck and whiskey make the point at a glance.

**Decisions to make**
- Hip-hop's list is mostly slurs and profanity. Options are to mask them ("n****"), filter them out to show skrrt, racks and gang, or group them as "strong profanity" and link to finding 2.
- Use single words and two-word phrases. Three-word phrases are too rare (most under 10% of songs) except for Party ("on the floor", "put your hands").
- Count each track once, even when it charted in several years.

## Optional extras

These use data already loaded but weren't covered by the planning hypotheses:

- **Emotion words:** anger, fear and negative words rose as a share of lyrics, within almost every genre (`word_emotion`, `word_vad`). Words are tagged with the NRC Emotion Lexicon (Mohammad & Turney, 2013) and the NRC VAD Lexicon (Mohammad, 2018).
- **Party songs follow unemployment:** the share of Party & Celebration songs rose and fell with the unemployment rate (r = 0.67) (`economic_observation`). Economic series are unemployment (U.S. Bureau of Labor Statistics, 2026) and consumer sentiment (University of Michigan, 2026), both from FRED.

## Caveats

- **No iTunes match:** 165 entries have neither a genre nor an explicit flag. They're left out of the genre and explicit charts.
- **No Spotify match:** 363 entries have no audio features (duration, valence, energy). Recent years are missing more of them.
- **Small yearly samples:** about 100 songs a year, and 22–47 for Pop. Use period comparisons for headline numbers and yearly lines for the overall shape.
- **Topics come from a model**, not hand labels.
- **Censored lyrics** ("f**k") aren't counted as profanity, so profanity rates are a floor.

## References

Apple Inc. (2026). *iTunes Search API* [Data set]. Retrieved October 16, 2026, from https://performance-partners.apple.com/search-api

Billboard. (2000–2024). *Year-end Hot 100 songs* [Data set]. https://www.billboard.com/charts/year-end/hot-100-songs/

Joshi, A. (2023). *Spotify_1Million_Tracks* [Data set]. Kaggle. https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks

Melo, T. de. (2026a). *Billboard Year-End Hot 100 lyrics dataset (2000–2024)* [Data set]. GitHub. https://github.com/tmelo-uea/billboard-hot100-lyrics

Melo, T. de. (2026b). Cross-provider consistency of LLM-based semantic enrichment for e-science workflows. In *Proceedings of the XX Brazilian e-Science Workshop (BreSci 2026)*. SBC Open Lib.

Mohammad, S. M. (2018). Obtaining reliable human ratings of valence, arousal, and dominance for 20,000 English words. In *Proceedings of the 56th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 174–184). Association for Computational Linguistics. https://doi.org/10.18653/v1/P18-1017

Mohammad, S. M., & Turney, P. D. (2013). Crowdsourcing a word–emotion association lexicon. *Computational Intelligence, 29*(3), 436–465. https://doi.org/10.1111/j.1467-8640.2012.00460.x

TypeSafe. (2026). *Jev* (Version 1.13.0) [Computer software].

U.S. Bureau of Labor Statistics. (2026). *Unemployment rate* [UNRATE] [Data set]. Federal Reserve Bank of St. Louis. Retrieved October 16, 2026, from https://fred.stlouisfed.org/series/UNRATE

University of Michigan. (2026). *University of Michigan: Consumer sentiment* [UMCSENT] [Data set]. Federal Reserve Bank of St. Louis. Retrieved October 16, 2026, from https://fred.stlouisfed.org/series/UMCSENT
