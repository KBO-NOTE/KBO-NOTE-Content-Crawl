CREATE SCHEMA IF NOT EXISTS kbonote;

CREATE TABLE IF NOT EXISTS kbonote.content (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,
  press TEXT NULL,
  url TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  creator TEXT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  crawled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  has_video BOOLEAN NOT NULL DEFAULT FALSE,
  representative_image_url TEXT NULL,
  like_count BIGINT NOT NULL DEFAULT 0,
  comment_count BIGINT NOT NULL DEFAULT 0,
  image_count BIGINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS kbonote.image (
  id BIGSERIAL PRIMARY KEY,
  content_id BIGINT NOT NULL,
  image_url TEXT NOT NULL,
  order_index BIGINT NULL,

  CONSTRAINT fk_content_image_content
    FOREIGN KEY (content_id)
    REFERENCES kbonote.content (id)
    ON DELETE CASCADE
);