"""Export core placement data from PostgreSQL to a portable SQLite file."""
import logging
import pathlib
import sqlite3

from src.database import get_conn

log = logging.getLogger(__name__)

_DEFAULT_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "placements.db"

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS source_university (
    university_id INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    domain        TEXT,
    country       TEXT,
    state         TEXT
);

CREATE TABLE IF NOT EXISTS placement (
    placement_id          INTEGER PRIMARY KEY,
    university_id         INTEGER REFERENCES source_university(university_id),
    university_name       TEXT,
    candidate_name        TEXT,
    graduation_year       INTEGER,
    field_of_study        TEXT,
    placement_institution TEXT,
    placement_position    TEXT,
    placement_sector      TEXT,
    is_postdoc            INTEGER,
    created_at            TEXT,
    updated_at            TEXT
);
"""


def export_to_sqlite(db_path: str | pathlib.Path | None = None):
    """Snapshot source_university and placement tables into a SQLite file.

    Replaces the file on each run so it's always a fresh, consistent snapshot.
    """
    db_path = pathlib.Path(db_path) if db_path else _DEFAULT_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove old file so we get a clean snapshot
    if db_path.exists():
        db_path.unlink()

    lite = sqlite3.connect(str(db_path))
    try:
        lite.executescript(_CREATE_TABLES)

        with get_conn() as pg:
            with pg.cursor() as cur:
                # --- source_university ---
                cur.execute(
                    "SELECT university_id, name, domain, country, state "
                    "FROM amm.source_university ORDER BY university_id"
                )
                rows = cur.fetchall()
                lite.executemany(
                    "INSERT INTO source_university VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
                log.info("Exported %d universities to SQLite", len(rows))

                # --- placement ---
                cur.execute(
                    "SELECT placement_id, university_id, university_name, "
                    "candidate_name, graduation_year, field_of_study, "
                    "placement_institution, placement_position, "
                    "placement_sector, is_postdoc::int, "
                    "created_at::text, updated_at::text "
                    "FROM amm.placement ORDER BY placement_id"
                )
                rows = cur.fetchall()
                lite.executemany(
                    "INSERT INTO placement VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                log.info("Exported %d placements to SQLite", len(rows))

        lite.commit()
        log.info("SQLite export complete: %s", db_path)
    finally:
        lite.close()
