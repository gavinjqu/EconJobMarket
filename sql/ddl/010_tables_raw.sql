CREATE TABLE IF NOT EXISTS amm.ingest_run (
  run_id      BIGSERIAL PRIMARY KEY,
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  git_sha     TEXT,
  notes       TEXT
);

CREATE TABLE IF NOT EXISTS amm.source_university (
  university_id BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  domain        TEXT,
  country       TEXT,
  state         TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS amm.source_page (
  page_id        BIGSERIAL PRIMARY KEY,
  university_id  BIGINT NOT NULL REFERENCES amm.source_university(university_id),
  page_type      TEXT NOT NULL, -- e.g., 'faculty_directory', 'departments'
  url            TEXT NOT NULL,
  is_dynamic     BOOLEAN NOT NULL DEFAULT FALSE,
  robots_allowed BOOLEAN,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (university_id, page_type, url)
);

CREATE TABLE IF NOT EXISTS amm.raw_fetch (
  fetch_id      BIGSERIAL PRIMARY KEY,
  run_id        BIGINT NOT NULL REFERENCES amm.ingest_run(run_id),
  page_id       BIGINT NOT NULL REFERENCES amm.source_page(page_id),
  fetched_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  status_code   INT,
  content_type  TEXT,
  body_text     TEXT,          -- simple start; later you can store file path or bytea
  body_hash     TEXT,
  error         TEXT
);
