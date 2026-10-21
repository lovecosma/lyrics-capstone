set search_path to billboard_lyrics;

create or replace view chart_entry as
select
  ct.chart_track_id,
  ch."year",
  ct."rank",
  t.track_id,
  t.title,
  t.artist_name,
  t.is_explicit,
  g."name" as genre,
  bg."name" as broad_genre
from chart_track ct
join chart ch on ch.chart_id = ct.chart_id
join track t on t.track_id = ct.track_id
left join track_genre tg on tg.track_id = t.track_id
left join genre g on g.genre_id = tg.genre_id
left join broad_genre bg on bg.broad_genre_id = g.broad_genre_id;

create or replace view genre_theme_year_count as
select
  ce."year",
  ce.broad_genre,
  tp.display_name as main_theme,
  lt.analysis_version as topic_analysis_version,
  count(*) as entry_count
from chart_entry ce
join lyrics_topic lt on lt.track_id = ce.track_id and lt.is_primary
join topic tp on tp.topic_id = lt.topic_id
group by ce."year", ce.broad_genre, tp.display_name, lt.analysis_version;

create or replace view genre_track as
select distinct track_id, broad_genre
from chart_entry
where broad_genre is not null;

create or replace view strong_profanity_word as
with core_profanity(word) as (
  values ('fuck'), ('shit'), ('bitch'), ('pussy'), ('dick'), ('ass')
),
missing_spelling(word) as (
  values ('ho'), ('hos'), ('thot'), ('thots')
)
select pw.word
from profanity_word pw
where pw.severity_description in ('Strong', 'Severe')
   or pw.canonical_form_1 in (select word from core_profanity)
   or pw.canonical_form_2 in (select word from core_profanity)
   or pw.canonical_form_3 in (select word from core_profanity)
union
select word from core_profanity
union
select word from missing_spelling;

create or replace view lyrics_word as
select
  lnm.track_id,
  lnm.ngram as word,
  lnm.frequency,
  lnm.analysis_version,
  spw.word is not null as is_explicit
from lyrics_ngram_metric lnm
left join strong_profanity_word spw on spw.word = lnm.ngram
where lnm.n = 1;

create or replace view track_topic as
select
  lt.track_id,
  tp.display_name as topic,
  lt.is_primary,
  lt.primary_probability,
  lt.presence_probability,
  lt.analysis_version
from lyrics_topic lt
join topic tp on tp.topic_id = lt.topic_id;
