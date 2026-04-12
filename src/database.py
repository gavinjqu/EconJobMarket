"""SQLite database layer."""
import csv
import logging
import pathlib
import sqlite3
from contextlib import contextmanager

log = logging.getLogger(__name__)

_DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "placements.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingest_run (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    git_sha     TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS source_university (
    university_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    domain        TEXT,
    country       TEXT,
    state         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS source_page (
    page_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    university_id  INTEGER NOT NULL REFERENCES source_university(university_id),
    page_type      TEXT NOT NULL,
    url            TEXT NOT NULL,
    is_dynamic     INTEGER NOT NULL DEFAULT 0,
    robots_allowed INTEGER,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (university_id, page_type, url)
);

CREATE TABLE IF NOT EXISTS raw_fetch (
    fetch_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        INTEGER NOT NULL REFERENCES ingest_run(run_id),
    page_id       INTEGER NOT NULL REFERENCES source_page(page_id),
    fetched_at    TEXT NOT NULL DEFAULT (datetime('now')),
    status_code   INTEGER,
    content_type  TEXT,
    body_text     TEXT,
    body_hash     TEXT,
    error         TEXT
);

CREATE TABLE IF NOT EXISTS stg_placement (
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
);

CREATE TABLE IF NOT EXISTS placement (
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
);
"""


def _db_path() -> pathlib.Path:
    return _DB_PATH


_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "universities.csv"


def init_db(db_path: pathlib.Path | None = None):
    """Create the database file, schema, and seed data if they don't exist."""
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    _seed_from_csv(conn)
    conn.commit()
    conn.close()


def _seed_from_csv(conn):
    """Seed source_university and source_page from config/universities.csv."""
    if not _CONFIG.exists():
        log.warning("Config file not found: %s", _CONFIG)
        return
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            conn.execute(
                "INSERT OR IGNORE INTO source_university (name, domain, country, state) "
                "VALUES (?, ?, 'US', ?)",
                (row["name"], row["domain"], row["state"]),
            )
            url = row.get("placement_url", "").strip()
            if url:
                uni = conn.execute(
                    "SELECT university_id FROM source_university WHERE name = ?",
                    (row["name"],),
                ).fetchone()
                if uni:
                    conn.execute(
                        "INSERT OR IGNORE INTO source_page "
                        "(university_id, page_type, url, is_dynamic, robots_allowed) "
                        "VALUES (?, 'placement', ?, 0, 1)",
                        (uni[0], url),
                    )


@contextmanager
def get_conn(db_path: pathlib.Path | None = None):
    path = db_path or _DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def close_pool():
    """No-op for backwards compatibility. SQLite doesn't use connection pooling."""
    pass


# --------------- insert helpers ---------------

def insert_ingest_run(conn, git_sha=None, notes=None):
    sql = "INSERT INTO ingest_run (git_sha, notes) VALUES (?, ?)"
    cur = conn.execute(sql, (git_sha, notes))
    return cur.lastrowid


def finish_ingest_run(conn, run_id):
    conn.execute(
        "UPDATE ingest_run SET finished_at = datetime('now') WHERE run_id = ?",
        (run_id,),
    )


def insert_raw_fetch(conn, run_id, page_id, status_code, content_type,
                     body_text, body_hash, error=None):
    sql = """
        INSERT INTO raw_fetch
            (run_id, page_id, status_code, content_type, body_text, body_hash, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cur = conn.execute(sql, (run_id, page_id, status_code, content_type,
                             body_text, body_hash, error))
    return cur.lastrowid


def insert_stg_placement(conn, fetch_id, university_id, raw_name, raw_field,
                         raw_placement, raw_position, raw_sector,
                         graduation_year, row_index, parse_error=None):
    sql = """
        INSERT INTO stg_placement
            (fetch_id, university_id, raw_name, raw_field, raw_placement,
             raw_position, raw_sector, graduation_year, row_index,
             parsed_at, parse_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
    """
    cur = conn.execute(sql, (fetch_id, university_id, raw_name, raw_field,
                             raw_placement, raw_position, raw_sector,
                             graduation_year, row_index, parse_error))
    return cur.lastrowid


def insert_placement(conn, stg_placement_id, university_id, university_name,
                     candidate_name, graduation_year, field_of_study,
                     placement_institution, placement_position,
                     placement_sector, is_postdoc):
    sql = """
        INSERT INTO placement
            (stg_placement_id, university_id, university_name,
             candidate_name, graduation_year, field_of_study,
             placement_institution, placement_position,
             placement_sector, is_postdoc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (university_id, candidate_name, graduation_year, placement_institution)
        DO UPDATE SET
            field_of_study        = EXCLUDED.field_of_study,
            placement_position    = EXCLUDED.placement_position,
            placement_sector      = EXCLUDED.placement_sector,
            is_postdoc            = EXCLUDED.is_postdoc,
            updated_at            = datetime('now')
    """
    cur = conn.execute(sql, (stg_placement_id, university_id, university_name,
                             candidate_name, graduation_year, field_of_study,
                             placement_institution, placement_position,
                             placement_sector, is_postdoc))
    # For upserts, lastrowid may be 0 on conflict update; query the actual id
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT placement_id FROM placement "
        "WHERE university_id = ? AND candidate_name = ? "
        "AND graduation_year = ? AND placement_institution = ?",
        (university_id, candidate_name, graduation_year, placement_institution),
    ).fetchone()
    return row[0] if row else None


def get_pages_for_university(conn, university_id):
    sql = """
        SELECT page_id, url, page_type, is_dynamic
        FROM source_page
        WHERE university_id = ?
        ORDER BY page_id
    """
    return conn.execute(sql, (university_id,)).fetchall()


def get_all_universities(conn):
    return conn.execute(
        "SELECT university_id, name FROM source_university ORDER BY university_id"
    ).fetchall()


def get_university_by_slug(conn, slug):
    """Look up a university by slug matched against the domain column."""
    sql = """
        SELECT university_id, name
        FROM source_university
        WHERE domain LIKE ?
        LIMIT 1
    """
    return conn.execute(sql, (f"%{slug}%",)).fetchone()


def get_university_by_name(conn, name):
    """Look up a university by exact name."""
    sql = """
        SELECT university_id, name
        FROM source_university
        WHERE name = ?
        LIMIT 1
    """
    return conn.execute(sql, (name,)).fetchone()


def get_unprocessed_staging(conn, run_id=None):
    """Get staging rows that haven't been transformed yet."""
    sql = """
        SELECT s.stg_placement_id, s.fetch_id, s.university_id,
               s.raw_name, s.raw_field, s.raw_placement,
               s.raw_position, s.raw_sector, s.graduation_year,
               u.name AS university_name
        FROM stg_placement s
        LEFT JOIN raw_fetch f ON f.fetch_id = s.fetch_id
        JOIN source_university u ON u.university_id = s.university_id
        WHERE s.parse_error IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM placement pl
              WHERE pl.stg_placement_id = s.stg_placement_id
          )
    """
    params = []
    if run_id is not None:
        sql += " AND (s.fetch_id IS NULL OR f.run_id = ?)"
        params.append(run_id)
    sql += " ORDER BY s.stg_placement_id"
    return conn.execute(sql, params).fetchall()
