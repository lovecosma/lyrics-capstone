drop schema if exists billboard_lyrics cascade;
create schema billboard_lyrics;
set search_path to billboard_lyrics;

create table genre (
  genre_id serial primary key,
  "name" varchar(50) not null unique
);

create table chart (
  chart_id serial primary key,
  "year" int not null unique
);

create table topic (
  topic_id serial primary key,
  "name" varchar(50) not null unique,
  display_name varchar(50) not null unique,
  description varchar(200) not null
);

create table track (
  track_id serial primary key,
  title varchar(200) not null,
  artist_name varchar(150) not null,
  lyrics text not null,
  danceability decimal(7, 6) null,
  energy decimal(7, 6) null,
  speechiness decimal(7, 6) null,
  acousticness decimal(7, 6) null,
  instrumentalness decimal(7, 6) null,
  liveness decimal(7, 6) null,
  valence decimal(7, 6) null,
  loudness decimal(6, 3) null,
  tempo decimal(6, 3) null,
  "key" smallint null,
  "mode" smallint null,
  time_signature smallint null,
  duration_ms int null,
  unique (title, artist_name)
);

create table track_genre (
  track_genre_id serial primary key,
  track_id int not null,
    constraint fk_track_genre_track_id
      foreign key (track_id)
      references track(track_id),
  genre_id int not null,
    constraint fk_track_genre_genre_id
      foreign key (genre_id)
      references genre(genre_id),
  unique (track_id, genre_id)
);

create table chart_track (
  chart_track_id serial primary key,
  chart_id int not null,
    constraint fk_chart_track_chart_id
      foreign key (chart_id)
      references chart(chart_id),
  track_id int not null,
    constraint fk_chart_track_track_id
      foreign key (track_id)
      references track(track_id),
  "rank" int not null check ("rank" > 0),
  unique (chart_id, "rank"),
  unique (chart_id, track_id)
);

create table lyrics_metric (
  lyrics_metric_id serial primary key,
  track_id int not null,
    constraint fk_lyrics_metric_track_id
      foreign key (track_id)
      references track(track_id),
  word_count int not null,
  unique_word_count int not null,
  lexical_diversity decimal(7, 3) null,
  average_word_length decimal(5, 3) null,
  analysis_version varchar(20) not null,
  unique (track_id, analysis_version)
);

create table lyrics_ngram_metric (
  lyrics_ngram_id serial primary key,
  track_id int not null,
    constraint fk_lyrics_ngram_metric_track_id
      foreign key (track_id)
      references track(track_id),
  ngram varchar(100) not null,
  n smallint not null check (n between 1 and 3),
  frequency int not null check (frequency > 0),
  analysis_version varchar(20) not null,
  unique (track_id, ngram, analysis_version)
);

create table lyrics_topic (
  track_id int not null,
    constraint fk_lyrics_topic_track_id
      foreign key (track_id)
      references track(track_id),
  topic_id int not null,
    constraint fk_lyrics_topic_topic_id
      foreign key (topic_id)
      references topic(topic_id),
  is_primary boolean not null,
  model_version varchar(50) not null,
  primary key (track_id, topic_id)
);
