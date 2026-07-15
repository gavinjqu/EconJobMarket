"""
Main scraper orchestrator.

Pipeline per program:
  1. Resolve the program (parser slugs are program slugs; default programs
     adopt their university's universities.csv slug)
  2. Create an ingest_run; resolve the source_page by exact
     (program, page_type, url) match, creating it if absent
  3. For each page: fetch HTML -> insert raw_fetch
  4. Parse HTML -> insert stg_placement rows (stamped with program_id)
  5. Transform staging -> core placement rows (program_id flows from staging,
     so re-attribution corrections stick across re-scrapes)
  6. Finish the ingest_run
"""

import csv
import logging
import pathlib
import subprocess
from contextlib import contextmanager

from src.database import (
    ensure_ready,
    finish_ingest_run,
    get_conn,
    get_or_create_source_page,
    get_program_by_slug,
    get_unprocessed_staging,
    insert_ingest_run,
    insert_placement,
    insert_raw_fetch,
    insert_stg_placement,
)
from src.parsers import PARSERS
from src.utils import (
    body_hash,
    classify_sector,
    clean_field,
    clean_name,
    clean_text,
    detect_postdoc,
    fetch_url,
)

log = logging.getLogger(__name__)

_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "universities.csv"


def _get_config_row(slug: str) -> dict | None:
    """Return the full config row for a slug from universities.csv."""
    if not _CONFIG.exists():
        return None
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            if row["slug"] == slug:
                return row
    return None


@contextmanager
def _nullcontext():
    yield None


def _git_sha():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
        ).strip()
    except Exception:
        return None


def run_scraper(target: str, dry_run: bool = False):
    if not dry_run:
        ensure_ready()

    if target == "all":
        slugs = list(PARSERS.keys())
    else:
        slugs = [target]

    for slug in slugs:
        log.info("=== Starting scrape for: %s ===", slug)
        try:
            _scrape_program(slug, dry_run)
        except Exception:
            log.exception("Failed to scrape %s", slug)


def _scrape_program(slug: str, dry_run: bool):
    parser_cls = PARSERS[slug]
    parser = parser_cls()

    program_id = university_id = run_id = page_id = None

    # URL comes from config (single source of truth). Parser slugs equal
    # universities.csv slugs for default programs; named programs get their
    # URLs from source_page rows seeded via config/programs.csv.
    config_row = _get_config_row(slug)
    url = config_row["placement_url"] if config_row else None

    if not dry_run:
        with get_conn() as conn:
            program = get_program_by_slug(conn, slug)
            if program is None:
                log.error("No program with slug '%s'. Run: python -m src migrate", slug)
                return
            program_id, university_id, program_name, university_name = program

            if not url:
                row = conn.execute(
                    "SELECT url FROM source_page "
                    "WHERE program_id = ? AND page_type = 'placement' ORDER BY page_id LIMIT 1",
                    (program_id,),
                ).fetchone()
                url = row[0] if row else None
            if not url:
                log.error("No placement URL for program '%s' (config or source_page)", slug)
                return

            page_id = get_or_create_source_page(conn, program_id, "placement", url)
            run_id = insert_ingest_run(conn, git_sha=_git_sha(), notes=f"scrape:{slug}")
            log.info("Created ingest_run %d for %s — %s", run_id, university_name, program_name)
    elif not url:
        log.error("No placement URL for slug '%s' in config", slug)
        return

    # --- Phase 1: Fetch and parse ---
    all_parsed = []

    fetch_ctx = get_conn() if not dry_run else _nullcontext()
    with fetch_ctx as conn:
        current_url = url
        log.info("Fetching page_id=%s url=%s", page_id, current_url)

        while current_url:
            html, status, ctype, error = "", None, None, None
            try:
                resp = fetch_url(current_url)
                html = resp.text
                status = resp.status_code
                ctype = resp.headers.get("Content-Type", "")
            except Exception as e:
                error = str(e)
                log.error("Fetch failed for %s: %s", current_url, e)

            if not dry_run:
                fetch_id = insert_raw_fetch(
                    conn,
                    run_id,
                    page_id,
                    status,
                    ctype,
                    html,
                    body_hash(html) if html else None,
                    error,
                )
            else:
                fetch_id = None

            if html and error is None:
                try:
                    parsed_rows = parser.parse(html, current_url)
                except Exception:
                    log.exception("Parse failed for %s", current_url)
                    parsed_rows = []
                all_parsed.append((fetch_id, parsed_rows))
                log.info("Parsed %d rows from %s", len(parsed_rows), current_url)

            next_url = parser.get_next_page_url(html, current_url) if html else None
            current_url = next_url

    # --- Phase 2: Insert staging rows ---
    if not dry_run:
        with get_conn() as conn:
            stg_count = 0
            for fetch_id, rows in all_parsed:
                for row in rows:
                    insert_stg_placement(
                        conn,
                        fetch_id,
                        university_id,
                        program_id,
                        raw_name=row.raw_name,
                        raw_field=row.raw_field,
                        raw_placement=row.raw_placement,
                        raw_position=row.raw_position,
                        raw_sector=None,
                        graduation_year=row.graduation_year,
                        row_index=row.row_index,
                    )
                    stg_count += 1
            log.info("Inserted %d staging rows", stg_count)

    # --- Phase 3: Transform staging -> core ---
    if not dry_run:
        with get_conn() as conn:
            unprocessed = get_unprocessed_staging(conn, run_id)
            core_count = locked_count = 0
            for row in unprocessed:
                (
                    stg_id,
                    fetch_id,
                    stg_program_id,
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
                sector = classify_sector((raw_placement or "") + " " + (raw_position or ""))
                postdoc = detect_postdoc(institution, position)

                if candidate and institution:
                    placement_id = insert_placement(
                        conn,
                        stg_id,
                        stg_program_id,
                        candidate,
                        grad_year,
                        field,
                        institution,
                        position,
                        sector,
                        postdoc,
                    )
                    if placement_id is None:
                        locked_count += 1  # human-corrected row; scraper may not touch
                    else:
                        core_count += 1
                else:
                    log.warning("Skipping stg_id=%d: missing name or placement", stg_id)
            log.info(
                "Inserted/updated %d core placement rows (%d locked rows left untouched)",
                core_count,
                locked_count,
            )

    # --- Phase 4: Finish ingest run ---
    if not dry_run:
        with get_conn() as conn:
            finish_ingest_run(conn, run_id)
            log.info("Finished ingest_run %d", run_id)
    else:
        total = sum(len(rows) for _, rows in all_parsed)
        log.info("[DRY RUN] Would have inserted %d rows for %s", total, slug)
