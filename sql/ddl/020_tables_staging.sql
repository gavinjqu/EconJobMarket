CREATE TABLE IF NOT EXISTS amm.stg_placement (
    stg_placement_id  BIGSERIAL    PRIMARY KEY,
    fetch_id          BIGINT       REFERENCES amm.raw_fetch(fetch_id),
    university_id     BIGINT       REFERENCES amm.source_university(university_id),
    raw_name          TEXT,
    raw_field         TEXT,
    raw_placement     TEXT,
    raw_position      TEXT,
    raw_sector        TEXT,
    graduation_year   INT,
    row_index         INT,
    parsed_at         TIMESTAMPTZ,
    parse_error       TEXT
);
