"""v2: program-centric restructure.

- `program` becomes the hub entity (1 university : N PhD programs); every
  university gets a default program that adopts its universities.csv slug, so
  existing parser registrations keep working.
- `source_page` and `placement` are rebuilt keyed to program_id.
- The placement natural key becomes a unique expression index with
  COALESCE(graduation_year,-1): SQLite treats NULLs as pairwise-distinct in
  plain UNIQUE constraints, which let ~1,259 duplicate NULL-year groups
  accumulate. Those duplicates are archived to migration_conflict, never
  silently deleted.
- placement gains human_locked (rows a human corrected; scrape upserts may
  not touch them) and drops the denormalized university_name/university_id
  (display goes through the v_placement view).

See docs/DESIGN-v2-programs-faculty.md §4/§8.
"""

import csv
import pathlib

from src.migrations.base import MigrationError, column_names, scalar, table_names

VERSION = 2
DESCRIPTION = (
    "program table; source_page/placement rebuilt onto program_id; "
    "NULL-year duplicate cleanup; human_locked; display + QC views"
)

_CONFIG = pathlib.Path(__file__).resolve().parent.parent.parent / "config" / "universities.csv"


def precondition(conn):
    tables = table_names(conn)
    if "program" in tables:
        raise MigrationError(
            "'program' table already exists but v2 is not recorded — the database "
            "may be half-migrated; restore the pre-migration backup"
        )
    missing = {"source_university", "source_page", "stg_placement", "placement"} - tables
    if missing:
        raise MigrationError(f"baseline tables missing: {sorted(missing)}")
    if "university_id" not in column_names(conn, "placement"):
        raise MigrationError("'placement' lacks university_id — not a v1 schema")
    if scalar(conn, "SELECT COUNT(*) FROM source_university") == 0:
        raise MigrationError("source_university is empty — v1 seeding did not run")
    bad_pages = scalar(conn, "SELECT COUNT(*) FROM source_page WHERE page_type <> 'placement'")
    if bad_pages:
        raise MigrationError(f"{bad_pages} source_page rows have unexpected page_type")
    bad_rows = scalar(
        conn,
        """SELECT COUNT(*) FROM placement
           WHERE candidate_name IS NULL OR candidate_name = ''
              OR placement_institution IS NULL OR placement_institution = ''
              OR (placement_sector IS NOT NULL AND placement_sector NOT IN
                  ('academic','private','government','other'))
              OR (graduation_year IS NOT NULL AND graduation_year NOT BETWEEN 1950 AND 2100)""",
    )
    if bad_rows:
        raise MigrationError(
            f"{bad_rows} placement rows violate the v2 constraints "
            "(null/empty name or institution, bad sector, or out-of-range year); "
            "inspect and clean them before migrating"
        )


def apply(conn):
    _create_program(conn)
    _seed_default_programs(conn)
    _rebuild_source_page(conn)
    _add_stg_program_id(conn)
    _dedup_and_rebuild_placement(conn)
    _create_verification_event(conn)
    _create_views(conn)


# ---------------------------------------------------------------------------


def _create_program(conn):
    conn.execute("""
        CREATE TABLE program (
            program_id    INTEGER PRIMARY KEY,
            university_id INTEGER NOT NULL REFERENCES source_university(university_id),
            slug          TEXT NOT NULL UNIQUE,
            name          TEXT NOT NULL,
            department    TEXT,
            degree        TEXT NOT NULL DEFAULT 'PhD',
            website_url   TEXT,
            is_default    INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0,1)),
            is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            notes         TEXT,
            created_at    TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (university_id, name)
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX ux_program_one_default ON program (university_id) WHERE is_default = 1"
    )


def _seed_default_programs(conn):
    """One default 'Economics PhD' program per university, slug from universities.csv."""
    if not _CONFIG.exists():
        raise MigrationError(f"config file not found: {_CONFIG}")
    slug_by_name = {}
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            slug_by_name[row["name"]] = row["slug"]

    unmatched = []
    for uni_id, name in conn.execute("SELECT university_id, name FROM source_university"):
        slug = slug_by_name.get(name)
        if slug is None:
            unmatched.append(name)
            continue
        conn.execute(
            "INSERT INTO program (university_id, slug, name, is_default) "
            "VALUES (?, ?, 'Economics PhD', 1)",
            (uni_id, slug),
        )
    if unmatched:
        raise MigrationError(
            f"{len(unmatched)} universities have no universities.csv row (no slug): {unmatched}"
        )
    without_default = scalar(
        conn,
        """SELECT COUNT(*) FROM source_university u
           WHERE NOT EXISTS (SELECT 1 FROM program p
                             WHERE p.university_id = u.university_id AND p.is_default = 1)""",
    )
    if without_default:
        raise MigrationError(f"{without_default} universities ended up without a default program")


def _rebuild_source_page(conn):
    old_count = scalar(conn, "SELECT COUNT(*) FROM source_page")
    conn.execute("""
        CREATE TABLE source_page_new (
            page_id        INTEGER PRIMARY KEY,
            program_id     INTEGER NOT NULL REFERENCES program(program_id),
            page_type      TEXT NOT NULL CHECK (page_type IN ('placement','directory')),
            url            TEXT NOT NULL,
            is_dynamic     INTEGER NOT NULL DEFAULT 0 CHECK (is_dynamic IN (0,1)),
            robots_allowed INTEGER,
            created_at     TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (program_id, page_type, url)
        )
    """)
    # page_id values are preserved so raw_fetch FKs stay valid.
    conn.execute("""
        INSERT INTO source_page_new
            (page_id, program_id, page_type, url, is_dynamic, robots_allowed, created_at)
        SELECT sp.page_id, pr.program_id, sp.page_type, sp.url,
               sp.is_dynamic, sp.robots_allowed, sp.created_at
        FROM source_page sp
        JOIN program pr ON pr.university_id = sp.university_id AND pr.is_default = 1
    """)
    new_count = scalar(conn, "SELECT COUNT(*) FROM source_page_new")
    if new_count != old_count:
        raise MigrationError(f"source_page rebuild lost rows: {old_count} -> {new_count}")
    conn.execute("DROP TABLE source_page")
    conn.execute("ALTER TABLE source_page_new RENAME TO source_page")


def _add_stg_program_id(conn):
    conn.execute(
        "ALTER TABLE stg_placement ADD COLUMN program_id INTEGER REFERENCES program(program_id)"
    )
    conn.execute("""
        UPDATE stg_placement
        SET program_id = (SELECT p.program_id FROM program p
                          WHERE p.university_id = stg_placement.university_id
                            AND p.is_default = 1)
        WHERE university_id IS NOT NULL
    """)
    unbackfilled = scalar(
        conn,
        "SELECT COUNT(*) FROM stg_placement WHERE university_id IS NOT NULL AND program_id IS NULL",
    )
    if unbackfilled:
        raise MigrationError(f"{unbackfilled} stg_placement rows could not be backfilled")


def _dedup_and_rebuild_placement(conn):
    old_count = scalar(conn, "SELECT COUNT(*) FROM placement")

    # Duplicate groups under the v2 natural key. Under the v1 key these could
    # only arise for NULL graduation_year (NULLs never conflict in UNIQUE).
    # Keep the earliest row per group; archive the rest as full JSON.
    conn.execute("""
        CREATE TEMP TABLE dropped_placement AS
        SELECT p.placement_id, k.keep_id
        FROM placement p
        JOIN (
            SELECT MIN(placement_id) AS keep_id,
                   university_id, candidate_name,
                   COALESCE(graduation_year, -1) AS year_key,
                   placement_institution
            FROM placement
            GROUP BY university_id, candidate_name,
                     COALESCE(graduation_year, -1), placement_institution
            HAVING COUNT(*) > 1
        ) k ON p.university_id = k.university_id
           AND p.candidate_name = k.candidate_name
           AND COALESCE(p.graduation_year, -1) = k.year_key
           AND p.placement_institution = k.placement_institution
           AND p.placement_id <> k.keep_id
    """)
    conn.execute("""
        INSERT INTO migration_conflict
            (migration_version, table_name, reason, kept_pk, dropped_row_json)
        SELECT 2, 'placement', 'natural-key-duplicate', d.keep_id,
               json_object(
                   'placement_id', p.placement_id,
                   'stg_placement_id', p.stg_placement_id,
                   'university_id', p.university_id,
                   'university_name', p.university_name,
                   'candidate_name', p.candidate_name,
                   'graduation_year', p.graduation_year,
                   'field_of_study', p.field_of_study,
                   'placement_institution', p.placement_institution,
                   'placement_position', p.placement_position,
                   'placement_sector', p.placement_sector,
                   'is_postdoc', p.is_postdoc,
                   'created_at', p.created_at,
                   'updated_at', p.updated_at)
        FROM placement p
        JOIN dropped_placement d ON d.placement_id = p.placement_id
    """)
    dropped = scalar(conn, "SELECT COUNT(*) FROM dropped_placement")

    conn.execute("""
        CREATE TABLE placement_new (
            placement_id          INTEGER PRIMARY KEY,
            stg_placement_id      INTEGER REFERENCES stg_placement(stg_placement_id),
            program_id            INTEGER NOT NULL REFERENCES program(program_id),
            candidate_name        TEXT NOT NULL CHECK (candidate_name <> ''),
            graduation_year       INTEGER CHECK (graduation_year BETWEEN 1950 AND 2100
                                                 OR graduation_year IS NULL),
            field_of_study_raw    TEXT,
            placement_institution TEXT NOT NULL CHECK (placement_institution <> ''),
            placement_position    TEXT,
            placement_sector      TEXT CHECK (placement_sector IN
                                              ('academic','private','government','other')),
            is_postdoc            INTEGER NOT NULL DEFAULT 0 CHECK (is_postdoc IN (0,1)),
            human_locked          INTEGER NOT NULL DEFAULT 0 CHECK (human_locked IN (0,1)),
            created_at            TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        INSERT INTO placement_new
            (placement_id, stg_placement_id, program_id, candidate_name, graduation_year,
             field_of_study_raw, placement_institution, placement_position,
             placement_sector, is_postdoc, human_locked, created_at, updated_at)
        SELECT p.placement_id, p.stg_placement_id, pr.program_id, p.candidate_name,
               p.graduation_year, p.field_of_study, p.placement_institution,
               p.placement_position, p.placement_sector, COALESCE(p.is_postdoc, 0), 0,
               COALESCE(p.created_at, datetime('now')), COALESCE(p.updated_at, datetime('now'))
        FROM placement p
        JOIN program pr ON pr.university_id = p.university_id AND pr.is_default = 1
        WHERE p.placement_id NOT IN (SELECT placement_id FROM dropped_placement)
    """)
    new_count = scalar(conn, "SELECT COUNT(*) FROM placement_new")
    if new_count != old_count - dropped:
        raise MigrationError(
            f"placement rebuild count mismatch: {old_count} - {dropped} dropped "
            f"!= {new_count} migrated"
        )
    conn.execute("DROP TABLE placement")
    conn.execute("ALTER TABLE placement_new RENAME TO placement")
    conn.execute("DROP TABLE dropped_placement")

    conn.execute("""
        CREATE UNIQUE INDEX ux_placement_natkey ON placement
            (program_id, candidate_name, COALESCE(graduation_year, -1), placement_institution)
    """)
    conn.execute(
        "CREATE INDEX ix_placement_program_year ON placement (program_id, graduation_year)"
    )
    conn.execute("CREATE INDEX ix_placement_institution ON placement (placement_institution)")
    conn.execute("""
        CREATE TRIGGER trg_placement_touch AFTER UPDATE ON placement
        BEGIN
            UPDATE placement SET updated_at = datetime('now')
            WHERE placement_id = NEW.placement_id;
        END
    """)


def _create_verification_event(conn):
    conn.execute("""
        CREATE TABLE verification_event (
            event_id     INTEGER PRIMARY KEY,
            entity_type  TEXT NOT NULL,
            entity_id    INTEGER NOT NULL,
            action       TEXT NOT NULL,
            payload_json TEXT,
            actor        TEXT NOT NULL,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX ix_verif_entity ON verification_event (entity_type, entity_id)")


def _create_views(conn):
    # Display denormalization lives here, not in core tables.
    conn.execute("""
        CREATE VIEW v_placement AS
        SELECT pl.placement_id,
               u.name          AS university_name,
               pr.slug         AS program_slug,
               pr.name         AS program_name,
               pr.department   AS program_department,
               pl.candidate_name,
               pl.graduation_year,
               pl.field_of_study_raw,
               pl.placement_institution,
               pl.placement_position,
               pl.placement_sector,
               pl.is_postdoc,
               pl.human_locked
        FROM placement pl
        JOIN program pr           ON pr.program_id = pl.program_id
        JOIN source_university u  ON u.university_id = pr.university_id
    """)
    # QC: the partial unique index enforces at-most-one default; this view
    # keeps at-least-one observable as new universities are added.
    conn.execute("""
        CREATE VIEW v_universities_without_default AS
        SELECT u.university_id, u.name
        FROM source_university u
        WHERE NOT EXISTS (SELECT 1 FROM program p
                          WHERE p.university_id = u.university_id AND p.is_default = 1)
    """)
    # QC: identical natural-key rows under two programs of one university —
    # the re-attribution double-count failure mode.
    conn.execute("""
        CREATE VIEW v_cross_program_dupes AS
        SELECT u.university_id,
               u.name AS university_name,
               pl.candidate_name,
               pl.graduation_year,
               pl.placement_institution,
               COUNT(DISTINCT pl.program_id) AS n_programs,
               COUNT(*)                      AS n_rows
        FROM placement pl
        JOIN program pr          ON pr.program_id = pl.program_id
        JOIN source_university u ON u.university_id = pr.university_id
        GROUP BY u.university_id, pl.candidate_name,
                 COALESCE(pl.graduation_year, -1), pl.placement_institution
        HAVING COUNT(DISTINCT pl.program_id) > 1
    """)
