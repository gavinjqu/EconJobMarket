"""SQLite database layer.

Schema lives in versioned migrations (src/migrations/); this module owns
connections and the insert/query helpers. Core tables carry no denormalized
display names — joins for display live in the v_placement view.
"""

import csv
import json
import logging
import pathlib
import sqlite3
import subprocess
from contextlib import contextmanager

from src.migrations.runner import apply_migrations, ensure_current

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_DB_PATH = _ROOT / "data" / "placements.db"
_PROGRAMS_CONFIG = _ROOT / "config" / "programs.csv"


def _db_path() -> pathlib.Path:
    return _DB_PATH


def init_db(db_path: pathlib.Path | None = None):
    """Create the database if needed and bring it to the latest schema version."""
    apply_migrations(db_path or _DB_PATH)


def ensure_ready(db_path: pathlib.Path | None = None):
    """Prepare the DB for a scrape/import run.

    A missing database is created and migrated; an existing database must
    already be at the current version (we never migrate implicitly on scrape —
    run `python -m src migrate` deliberately).
    """
    path = db_path or _DB_PATH
    if not path.exists():
        apply_migrations(path)
        return
    with get_conn(path) as conn:
        ensure_current(conn)


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


# --------------- ingest bookkeeping ---------------


def insert_ingest_run(conn, git_sha=None, notes=None):
    sql = "INSERT INTO ingest_run (git_sha, notes) VALUES (?, ?)"
    cur = conn.execute(sql, (git_sha, notes))
    return cur.lastrowid


def finish_ingest_run(conn, run_id):
    conn.execute(
        "UPDATE ingest_run SET finished_at = datetime('now') WHERE run_id = ?",
        (run_id,),
    )


def insert_raw_fetch(
    conn, run_id, page_id, status_code, content_type, body_text, body_hash, error=None
):
    sql = """
        INSERT INTO raw_fetch
            (run_id, page_id, status_code, content_type, body_text, body_hash, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    cur = conn.execute(
        sql, (run_id, page_id, status_code, content_type, body_text, body_hash, error)
    )
    return cur.lastrowid


# --------------- programs & pages ---------------


def get_program_by_slug(conn, slug):
    """Return (program_id, university_id, program_name, university_name) or None."""
    sql = """
        SELECT p.program_id, p.university_id, p.name, u.name
        FROM program p
        JOIN source_university u ON u.university_id = p.university_id
        WHERE p.slug = ?
    """
    return conn.execute(sql, (slug,)).fetchone()


def get_or_create_source_page(conn, program_id, page_type, url):
    """Resolve a source_page by exact (program, type, url), creating it if absent."""
    row = conn.execute(
        "SELECT page_id FROM source_page WHERE program_id = ? AND page_type = ? AND url = ?",
        (program_id, page_type, url),
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO source_page (program_id, page_type, url, is_dynamic, robots_allowed) "
        "VALUES (?, ?, ?, 0, 1)",
        (program_id, page_type, url),
    )
    return cur.lastrowid


def seed_programs(conn, csv_path: pathlib.Path | None = None):
    """Idempotently load named programs (and their pages) from config/programs.csv.

    Columns: university_slug, program_slug, name, department, degree,
    website_url, placement_url, faculty_directory_url. university_slug refers
    to the university's default-program slug (= universities.csv slug).
    """
    path = csv_path or _PROGRAMS_CONFIG
    if not path.exists():
        raise FileNotFoundError(f"programs config not found: {path}")
    created = pages = 0
    with open(path, newline="") as f:
        for line_no, row in enumerate(csv.DictReader(f), start=2):
            default = get_program_by_slug(conn, row["university_slug"].strip())
            if default is None:
                raise ValueError(
                    f"{path.name} line {line_no}: unknown university_slug "
                    f"'{row['university_slug']}'"
                )
            _, university_id, _, _ = default
            program_slug = row["program_slug"].strip()
            cur = conn.execute(
                "INSERT OR IGNORE INTO program "
                "(university_id, slug, name, department, degree, website_url, is_default) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (
                    university_id,
                    program_slug,
                    row["name"].strip(),
                    (row.get("department") or "").strip() or None,
                    (row.get("degree") or "PhD").strip() or "PhD",
                    (row.get("website_url") or "").strip() or None,
                ),
            )
            created += cur.rowcount
            program = get_program_by_slug(conn, program_slug)
            if program is None:
                raise ValueError(
                    f"{path.name} line {line_no}: slug '{program_slug}' already belongs "
                    "to a different program row (slug collision)"
                )
            program_id = program[0]
            for page_type, col in (
                ("placement", "placement_url"),
                ("directory", "faculty_directory_url"),
            ):
                url = (row.get(col) or "").strip()
                if url:
                    before = conn.execute("SELECT COUNT(*) FROM source_page").fetchone()[0]
                    get_or_create_source_page(conn, program_id, page_type, url)
                    after = conn.execute("SELECT COUNT(*) FROM source_page").fetchone()[0]
                    pages += after - before
    log.info("seed_programs: %d new programs, %d new pages", created, pages)
    return created, pages


# --------------- staging ---------------


def insert_stg_placement(
    conn,
    fetch_id,
    university_id,
    program_id,
    raw_name,
    raw_field,
    raw_placement,
    raw_position,
    raw_sector,
    graduation_year,
    row_index,
    parse_error=None,
):
    sql = """
        INSERT INTO stg_placement
            (fetch_id, university_id, program_id, raw_name, raw_field, raw_placement,
             raw_position, raw_sector, graduation_year, row_index,
             parsed_at, parse_error)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
    """
    cur = conn.execute(
        sql,
        (
            fetch_id,
            university_id,
            program_id,
            raw_name,
            raw_field,
            raw_placement,
            raw_position,
            raw_sector,
            graduation_year,
            row_index,
            parse_error,
        ),
    )
    return cur.lastrowid


def get_unprocessed_staging(conn, run_id=None):
    """Staging rows not yet transformed. placement.program_id derives from
    stg_placement.program_id, so re-attribution corrections stick."""
    sql = """
        SELECT s.stg_placement_id, s.fetch_id, s.program_id,
               s.raw_name, s.raw_field, s.raw_placement,
               s.raw_position, s.raw_sector, s.graduation_year
        FROM stg_placement s
        LEFT JOIN raw_fetch f ON f.fetch_id = s.fetch_id
        WHERE s.parse_error IS NULL
          AND s.program_id IS NOT NULL
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


# --------------- core placement ---------------

_PLACEMENT_UPSERT = """
    INSERT INTO placement
        (stg_placement_id, program_id, candidate_name, graduation_year,
         field_of_study_raw, placement_institution, placement_position,
         placement_sector, is_postdoc)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (program_id, candidate_name, COALESCE(graduation_year, -1),
                 placement_institution)
    DO UPDATE SET
        stg_placement_id   = EXCLUDED.stg_placement_id,
        field_of_study_raw = EXCLUDED.field_of_study_raw,
        placement_position = EXCLUDED.placement_position,
        placement_sector   = EXCLUDED.placement_sector,
        is_postdoc         = EXCLUDED.is_postdoc,
        updated_at         = datetime('now')
    WHERE placement.human_locked = 0
    RETURNING placement_id
"""


def insert_placement(
    conn,
    stg_placement_id,
    program_id,
    candidate_name,
    graduation_year,
    field_of_study_raw,
    placement_institution,
    placement_position,
    placement_sector,
    is_postdoc,
):
    """Upsert a placement. Returns placement_id, or None when the existing row
    is human_locked (a hand-verified correction the scraper may not touch)."""
    row = conn.execute(
        _PLACEMENT_UPSERT,
        (
            stg_placement_id,
            program_id,
            candidate_name,
            graduation_year,
            field_of_study_raw,
            placement_institution,
            placement_position,
            placement_sector,
            1 if is_postdoc else 0,
        ),
    ).fetchone()
    return row[0] if row else None


# --------------- curation ---------------

EDITABLE_PLACEMENT_FIELDS = {
    "candidate_name",
    "graduation_year",
    "field_of_study_raw",
    "placement_institution",
    "placement_position",
    "placement_sector",
    "is_postdoc",
}


def _actor() -> str:
    try:
        name = subprocess.check_output(
            ["git", "config", "user.name"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if name:
            return name
    except Exception:
        pass
    import getpass

    return getpass.getuser()


def edit_placement(conn, placement_id, changes: dict, unlock: bool = False):
    """Apply a human correction to a placement row.

    Sets human_locked=1 (or 0 with unlock=True) so scrape upserts can't clobber
    it, and records a verification_event with the before/after values.
    Returns the (before, after) row dicts.
    """
    bad = set(changes) - EDITABLE_PLACEMENT_FIELDS
    if bad:
        raise ValueError(
            f"not editable: {sorted(bad)} (allowed: {sorted(EDITABLE_PLACEMENT_FIELDS)})"
        )
    if not changes and not unlock:
        raise ValueError("nothing to do: no field changes and no --unlock")

    cols = sorted(EDITABLE_PLACEMENT_FIELDS) + ["human_locked", "program_id"]
    row = conn.execute(
        f"SELECT {', '.join(cols)} FROM placement WHERE placement_id = ?", (placement_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"no placement with id {placement_id}")
    before = dict(zip(cols, row))

    assignments = [f"{col} = ?" for col in changes]
    params = list(changes.values())
    assignments.append("human_locked = ?")
    params.append(0 if unlock else 1)
    params.append(placement_id)
    conn.execute(f"UPDATE placement SET {', '.join(assignments)} WHERE placement_id = ?", params)

    after = {**before, **changes, "human_locked": 0 if unlock else 1}
    conn.execute(
        "INSERT INTO verification_event (entity_type, entity_id, action, payload_json, actor) "
        "VALUES ('placement', ?, ?, ?, ?)",
        (
            placement_id,
            "unlock" if unlock and not changes else "edit",
            json.dumps({"before": before, "after": after}),
            _actor(),
        ),
    )
    return before, after
