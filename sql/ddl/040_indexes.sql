-- raw layer
CREATE INDEX IF NOT EXISTS idx_raw_fetch_run    ON amm.raw_fetch (run_id);
CREATE INDEX IF NOT EXISTS idx_raw_fetch_page   ON amm.raw_fetch (page_id);

-- staging layer
CREATE INDEX IF NOT EXISTS idx_stg_placement_fetch      ON amm.stg_placement (fetch_id);
CREATE INDEX IF NOT EXISTS idx_stg_placement_university  ON amm.stg_placement (university_id);
CREATE INDEX IF NOT EXISTS idx_stg_placement_year        ON amm.stg_placement (graduation_year);

-- core layer
CREATE INDEX IF NOT EXISTS idx_placement_university  ON amm.placement (university_id);
CREATE INDEX IF NOT EXISTS idx_placement_year         ON amm.placement (graduation_year);
CREATE INDEX IF NOT EXISTS idx_placement_stg          ON amm.placement (stg_placement_id);
CREATE INDEX IF NOT EXISTS idx_placement_sector       ON amm.placement (placement_sector);
