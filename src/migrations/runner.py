"""Versioned migration runner for data/placements.db.

Discipline (docs/DESIGN-v2-programs-faculty.md §8):
- The connection runs in true autocommit (isolation_level=None) and the runner
  issues explicit BEGIN IMMEDIATE / COMMIT around each migration.
  executescript() is never used — it silently commits any open transaction.
- Every migration declares a structural precondition that runs before any
  write, so a half-migrated database fails loudly instead of re-applying.
- A VACUUM INTO backup (WAL-safe, consistent snapshot) is taken before the
  first pending migration touches an existing database.
- PRAGMA foreign_key_check must come back clean before commit.
"""

import logging
import pathlib
import sqlite3
import time

from src.migrations import MIGRATIONS
from src.migrations.base import MigrationError

log = logging.getLogger(__name__)

_BOOKKEEPING = [
    """CREATE TABLE IF NOT EXISTS schema_migration (
        version     INTEGER PRIMARY KEY,
        applied_at  TEXT NOT NULL DEFAULT (datetime('now')),
        description TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS migration_conflict (
        conflict_id       INTEGER PRIMARY KEY,
        migration_version INTEGER NOT NULL,
        table_name        TEXT NOT NULL,
        reason            TEXT NOT NULL,
        kept_pk           INTEGER,
        dropped_row_json  TEXT NOT NULL,
        created_at        TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
]

LATEST_VERSION = max(m.VERSION for m in MIGRATIONS)


def current_version(conn) -> int:
    has_table = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='schema_migration'"
    ).fetchone()[0]
    if not has_table:
        return 0
    return conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migration").fetchone()[0]


def pending_migrations(conn):
    version = current_version(conn)
    return [m for m in MIGRATIONS if m.VERSION > version]


def ensure_current(conn):
    """Raise if the connected database is behind the code's schema version."""
    pending = pending_migrations(conn)
    if pending:
        versions = ", ".join(f"v{m.VERSION}" for m in pending)
        raise MigrationError(
            f"database schema is behind ({versions} pending) — run: python -m src migrate"
        )


def apply_migrations(db_path: pathlib.Path):
    """Bring the database at db_path to the latest schema version."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), isolation_level=None)  # true autocommit
    try:
        pending = pending_migrations(conn)
        if not pending:
            log.info("Database is up to date (v%d)", current_version(conn))
            return
        is_empty = (
            conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0] == 0
        )
        if not is_empty:
            _backup(conn, db_path, pending[0].VERSION)
        for migration in pending:
            _apply_one(conn, migration)
        # Fold the WAL into the main file so the .db is complete on its own
        # (it is committed to git as the dataset artifact).
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        log.info("Database is now at v%d", current_version(conn))
    finally:
        conn.close()


def _backup(conn, db_path: pathlib.Path, first_pending_version: int) -> pathlib.Path:
    backups = db_path.parent / "backups"
    backups.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = backups / f"{db_path.stem}-pre-v{first_pending_version}-{stamp}.db"
    if dest.exists():
        raise MigrationError(f"backup target already exists: {dest}")
    conn.execute("VACUUM INTO ?", (str(dest),))
    log.info("Backup written to %s", dest)
    return dest


def _apply_one(conn, migration):
    log.info("Applying migration v%d: %s", migration.VERSION, migration.DESCRIPTION)
    # foreign_keys is a no-op inside a transaction, so set it before BEGIN.
    # It stays OFF during rebuild migrations (tables are recreated out of
    # dependency order); integrity is proven by foreign_key_check instead.
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN IMMEDIATE")
    try:
        for stmt in _BOOKKEEPING:
            conn.execute(stmt)
        already = conn.execute(
            "SELECT 1 FROM schema_migration WHERE version = ?", (migration.VERSION,)
        ).fetchone()
        if already:
            raise MigrationError(f"v{migration.VERSION} already recorded — refusing to re-apply")
        migration.precondition(conn)
        migration.apply(conn)
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise MigrationError(f"foreign_key_check failed: {violations[:10]}")
        conn.execute(
            "INSERT INTO schema_migration (version, description) VALUES (?, ?)",
            (migration.VERSION, migration.DESCRIPTION),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
    log.info("Migration v%d applied", migration.VERSION)
