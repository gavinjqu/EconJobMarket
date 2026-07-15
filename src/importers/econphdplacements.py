"""Import placement data from econphdplacements.com JSONL dataset.

Downloads the JSONL from the site (or reads a cached local copy),
maps fields to our stg_placement schema, and runs the staging→core
transform. Records land in each university's default program (the external
dataset is department-level; its department_id values match our
universities.csv slugs, which default programs adopt).

Usage:
    python -m src import econphdplacements [--dry-run]
"""

import csv
import json
import logging
import pathlib

import requests

from src.database import (
    ensure_ready,
    finish_ingest_run,
    get_conn,
    get_program_by_slug,
    get_unprocessed_staging,
    insert_ingest_run,
    insert_placement,
    insert_stg_placement,
)
from src.utils import classify_sector, clean_field, clean_name, clean_text, detect_postdoc

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"
_CACHE_DIR = _ROOT / "data" / "imports"
_CACHE_FILE = _CACHE_DIR / "all_placements.jsonl"
_DATA_URL = "https://econphdplacements.com/data/all_placements.jsonl"

# Map external categories to our sector values
_CATEGORY_MAP = {
    "tenure_track": "academic",
    "other_academic": "academic",
    "private_sector": "private",
    "central_banks": "government",
    "government": "government",
    "international_orgs": "government",
    "think_tanks": "other",
}


def _load_config() -> dict[str, dict]:
    """Load config and build slug → config row mapping."""
    mapping = {}
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            mapping[row["slug"]] = row
    return mapping


def _download_jsonl() -> pathlib.Path:
    """Download the JSONL file if not already cached."""
    if _CACHE_FILE.exists() and _CACHE_FILE.stat().st_size > 0:
        log.info("Using cached JSONL: %s", _CACHE_FILE)
        return _CACHE_FILE

    log.info("Downloading JSONL from %s ...", _DATA_URL)
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    resp = requests.get(_DATA_URL, timeout=60)
    resp.raise_for_status()
    _CACHE_FILE.write_bytes(resp.content)
    log.info("Downloaded %d bytes", len(resp.content))
    return _CACHE_FILE


def _resolve_programs(conn, config: dict) -> dict[str, tuple[int, int]]:
    """Map external department_id → (program_id, university_id).

    department_id values equal our universities.csv slugs, which each
    university's default program adopts.
    """
    mapping = {}
    for slug in config:
        program = get_program_by_slug(conn, slug)
        if program:
            mapping[slug] = (program[0], program[1])
        else:
            log.debug("No program for slug '%s'", slug)
    return mapping


def run_import(dry_run: bool = False):
    config = _load_config()
    target_slugs = set(config.keys())
    jsonl_path = _download_jsonl()

    # Load all records, filter to target US schools
    records = []
    with open(jsonl_path) as f:
        for line in f:
            rec = json.loads(line)
            dept = rec.get("department_id", "")
            if dept in target_slugs:
                records.append(rec)

    log.info(
        "Loaded %d records for target schools (from %d total)",
        len(records),
        sum(1 for _ in open(jsonl_path)),
    )

    if dry_run:
        # Show summary by department
        counts = {}
        for rec in records:
            d = rec["department_id"]
            counts[d] = counts.get(d, 0) + 1
        log.info("[DRY RUN] Would import %d records:", len(records))
        for slug in sorted(counts, key=lambda s: -counts[s]):
            log.info("  %-20s %d records", slug, counts[slug])
        return

    ensure_ready()

    # Resolve programs from database
    with get_conn() as conn:
        program_map = _resolve_programs(conn, config)

    if not program_map:
        log.error("No programs found in database. Run: python -m src migrate")
        return

    log.info("Resolved %d programs from database", len(program_map))

    # Create ingest run
    with get_conn() as conn:
        run_id = insert_ingest_run(conn, notes="import:econphdplacements")
        log.info("Created ingest_run %d", run_id)

    # Insert staging rows
    stg_count = 0
    skipped = 0
    with get_conn() as conn:
        for i, rec in enumerate(records):
            dept = rec["department_id"]
            if dept not in program_map:
                skipped += 1
                continue

            program_id, university_id = program_map[dept]
            category = rec.get("category") or ""
            raw_sector = _CATEGORY_MAP.get(category, "other")

            insert_stg_placement(
                conn,
                fetch_id=None,
                university_id=university_id,
                program_id=program_id,
                raw_name=rec.get("name") or "",
                raw_field=rec.get("field"),
                raw_placement=rec.get("placement"),
                raw_position=None,
                raw_sector=raw_sector,
                graduation_year=rec.get("year"),
                row_index=i,
            )
            stg_count += 1

    log.info("Inserted %d staging rows (%d skipped — no DB entry)", stg_count, skipped)

    # Transform staging → core
    with get_conn() as conn:
        unprocessed = get_unprocessed_staging(conn, run_id)
        core_count = locked_count = 0
        for row in unprocessed:
            (
                stg_id,
                fetch_id,
                program_id,
                raw_name,
                raw_field,
                raw_placement,
                raw_position,
                raw_sector,
                grad_year,
            ) = row

            candidate = clean_name(raw_name)
            field = clean_field(raw_field)
            institution = clean_text(raw_placement)
            position = clean_text(raw_position)

            # For imported data, prefer the pre-mapped sector from the source;
            # fall back to our classifier if raw_sector is empty.
            sector = raw_sector or classify_sector(
                (raw_placement or "") + " " + (raw_position or "")
            )
            postdoc = detect_postdoc(institution, position)

            if candidate and institution:
                placement_id = insert_placement(
                    conn,
                    stg_id,
                    program_id,
                    candidate,
                    grad_year,
                    field,
                    institution,
                    position,
                    sector,
                    postdoc,
                )
                if placement_id is None:
                    locked_count += 1  # human-corrected row; import may not touch
                else:
                    core_count += 1
            else:
                log.warning("Skipping stg_id=%d: missing name or placement", stg_id)
        log.info(
            "Inserted/updated %d core placement rows (%d locked rows left untouched)",
            core_count,
            locked_count,
        )

    # Finish ingest run
    with get_conn() as conn:
        finish_ingest_run(conn, run_id)
        log.info("Finished ingest_run %d", run_id)
