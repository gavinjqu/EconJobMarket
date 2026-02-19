CREATE TABLE IF NOT EXISTS amm.placement (
    placement_id          BIGSERIAL    PRIMARY KEY,
    stg_placement_id      BIGINT       REFERENCES amm.stg_placement(stg_placement_id),
    university_id         BIGINT       REFERENCES amm.source_university(university_id),
    university_name       TEXT,
    candidate_name        TEXT,
    graduation_year       INT,
    field_of_study        TEXT,
    placement_institution TEXT,
    placement_position    TEXT,
    placement_sector      TEXT,
    is_postdoc            BOOLEAN      DEFAULT FALSE,
    created_at            TIMESTAMPTZ  DEFAULT now(),
    updated_at            TIMESTAMPTZ  DEFAULT now(),

    UNIQUE (university_id, candidate_name, graduation_year, placement_institution)
);
