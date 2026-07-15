"""v1 baseline: the original six-table schema plus university seed data.

Idempotent (CREATE TABLE IF NOT EXISTS / INSERT OR IGNORE), so an empty file
and a pre-versioning database both converge on the same v1 state.
"""

import csv
import pathlib

from src.migrations.base import MigrationError, column_names

VERSION = 1
DESCRIPTION = "baseline schema + seed universities from config/universities.csv"

_CONFIG = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "universities.csv"

STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS ingest_run (
        run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at  TEXT NOT NULL DEFAULT (datetime('now')),
        finished_at TEXT,
        git_sha     TEXT,
        notes       TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS source_university (
        university_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL UNIQUE,
        domain        TEXT,
        country       TEXT,
        state         TEXT,
        created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS source_page (
        page_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        university_id  INTEGER NOT NULL REFERENCES source_university(university_id),
        page_type      TEXT NOT NULL,
        url            TEXT NOT NULL,
        is_dynamic     INTEGER NOT NULL DEFAULT 0,
        robots_allowed INTEGER,
        created_at     TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE (university_id, page_type, url)
    )""",
    """CREATE TABLE IF NOT EXISTS raw_fetch (
        fetch_id      INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id        INTEGER NOT NULL REFERENCES ingest_run(run_id),
        page_id       INTEGER NOT NULL REFERENCES source_page(page_id),
        fetched_at    TEXT NOT NULL DEFAULT (datetime('now')),
        status_code   INTEGER,
        content_type  TEXT,
        body_text     TEXT,
        body_hash     TEXT,
        error         TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS stg_placement (
        stg_placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
        fetch_id         INTEGER REFERENCES raw_fetch(fetch_id),
        university_id    INTEGER REFERENCES source_university(university_id),
        raw_name         TEXT,
        raw_field        TEXT,
        raw_placement    TEXT,
        raw_position     TEXT,
        raw_sector       TEXT,
        graduation_year  INTEGER,
        row_index        INTEGER,
        parsed_at        TEXT,
        parse_error      TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS placement (
        placement_id          INTEGER PRIMARY KEY AUTOINCREMENT,
        stg_placement_id      INTEGER REFERENCES stg_placement(stg_placement_id),
        university_id         INTEGER REFERENCES source_university(university_id),
        university_name       TEXT,
        candidate_name        TEXT,
        graduation_year       INTEGER,
        field_of_study        TEXT,
        placement_institution TEXT,
        placement_position    TEXT,
        placement_sector      TEXT,
        is_postdoc            INTEGER DEFAULT 0,
        created_at            TEXT DEFAULT (datetime('now')),
        updated_at            TEXT DEFAULT (datetime('now')),
        UNIQUE (university_id, candidate_name, graduation_year, placement_institution)
    )""",
]


def precondition(conn):
    # Runs on empty files and on legacy pre-versioning databases. If a
    # placement table already exists it must still be the v1 shape — anything
    # else means the file drifted from any schema this code ever produced.
    cols = column_names(conn, "placement")
    if cols and "university_id" not in cols:
        raise MigrationError(
            "existing 'placement' table does not match the v1 baseline schema; "
            "this database needs manual inspection before migrating"
        )


def apply(conn):
    for stmt in STATEMENTS:
        conn.execute(stmt)
    _seed(conn)


def _seed(conn):
    if not _CONFIG.exists():
        raise MigrationError(f"config file not found: {_CONFIG}")
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            conn.execute(
                "INSERT OR IGNORE INTO source_university (name, domain, country, state) "
                "VALUES (?, ?, 'US', ?)",
                (row["name"], row["domain"], row["state"]),
            )
            url = (row.get("placement_url") or "").strip()
            if url:
                conn.execute(
                    "INSERT OR IGNORE INTO source_page "
                    "(university_id, page_type, url, is_dynamic, robots_allowed) "
                    "SELECT university_id, 'placement', ?, 0, 1 "
                    "FROM source_university WHERE name = ?",
                    (url, row["name"]),
                )
