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
