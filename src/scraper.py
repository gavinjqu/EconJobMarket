"""
Main scraper orchestrator.

Pipeline per university:
  1. Look up source_page rows for the university
  2. Create an ingest_run
  3. For each page: fetch HTML -> insert raw_fetch
  4. Parse HTML -> insert stg_placement rows
  5. Transform staging -> core placement rows
  6. Finish the ingest_run
"""

import csv
import logging
import pathlib
import subprocess
from contextlib import contextmanager

from src.database import (
    finish_ingest_run,
    get_conn,
    get_pages_for_university,
    get_university_by_name,
    get_university_by_slug,
    get_unprocessed_staging,
    init_db,
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


def _get_placement_url(slug: str) -> str | None:
    """Look up the placement URL for a slug from config/universities.csv."""
    if not _CONFIG.exists():
        return None
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            if row["slug"] == slug:
                return row["placement_url"] or None
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
        init_db()

    if target == "all":
        slugs = list(PARSERS.keys())
    else:
        slugs = [target]

    for slug in slugs:
        log.info("=== Starting scrape for: %s ===", slug)
        try:
            _scrape_university(slug, dry_run)
        except Exception:
            log.exception("Failed to scrape %s", slug)


def _get_config_row(slug: str) -> dict | None:
    """Return the full config row for a slug from universities.csv."""
    if not _CONFIG.exists():
        return None
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            if row["slug"] == slug:
                return row
    return None


def _scrape_university(slug: str, dry_run: bool):
    parser_cls = PARSERS[slug]
    parser = parser_cls()

    university_id = university_name = run_id = None
    page_id = None

    # Always get URL from config (single source of truth)
    config_row = _get_config_row(slug)
    url = config_row["placement_url"] if config_row else None
    if not url:
        url = _get_placement_url(slug)
    if not url:
        log.error("No placement URL for slug '%s' in config", slug)
        return

    pages = [(None, url, "placement", False)]

    if not dry_run:
        with get_conn() as conn:
            # Try to find university by name first, then by slug
            university = None
            if config_row:
                university = get_university_by_name(conn, config_row["name"])
            if university is None:
                university = get_university_by_slug(conn, slug)
            if university is None:
                log.error("No university with slug '%s'. Run seed data first.", slug)
                return
            university_id, university_name = university

            # Use source_page if available (for page_id tracking)
            db_pages = get_pages_for_university(conn, university_id)
            if db_pages:
                # Use the first page_id for raw_fetch tracking
                page_id = db_pages[0][0]

            run_id = insert_ingest_run(conn, git_sha=_git_sha(), notes=f"scrape:{slug}")
            log.info("Created ingest_run %d for %s", run_id, university_name)

    # --- Phase 1: Fetch and parse ---
    all_parsed = []

    fetch_ctx = get_conn() if not dry_run else _nullcontext()
    with fetch_ctx as conn:
        for _pid, url, page_type, is_dynamic in pages:
            # Use DB page_id if available, otherwise fall back to pages list
            effective_page_id = page_id if page_id is not None else _pid
            log.info("Fetching page_id=%s url=%s", effective_page_id, url)
            current_url = url

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
                        effective_page_id,
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
                    all_parsed.append((effective_page_id, fetch_id, parsed_rows))
                    log.info("Parsed %d rows from %s", len(parsed_rows), current_url)

                next_url = parser.get_next_page_url(html, current_url) if html else None
                current_url = next_url

    # --- Phase 2: Insert staging rows ---
    if not dry_run:
        with get_conn() as conn:
            stg_count = 0
            for page_id, fetch_id, rows in all_parsed:
                for row in rows:
                    insert_stg_placement(
                        conn,
                        fetch_id,
                        university_id,
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
            core_count = 0
            for row in unprocessed:
                (
                    stg_id,
                    fetch_id,
                    uni_id,
                    raw_name,
                    raw_field,
                    raw_placement,
                    raw_position,
                    raw_sector,
                    grad_year,
                    uni_name,
                ) = row

                candidate = clean_name(raw_name)
                field = clean_field(raw_field)
                institution = clean_text(raw_placement)
                position = clean_text(raw_position)
                sector = classify_sector((raw_placement or "") + " " + (raw_position or ""))
                postdoc = detect_postdoc(institution, position)

                if candidate and institution:
                    insert_placement(
                        conn,
                        stg_id,
                        uni_id,
                        uni_name,
                        candidate,
                        grad_year,
                        field,
                        institution,
                        position,
                        sector,
                        postdoc,
                    )
                    core_count += 1
                else:
                    log.warning("Skipping stg_id=%d: missing name or placement", stg_id)
            log.info("Inserted/updated %d core placement rows", core_count)

    # --- Phase 4: Finish ingest run ---
    if not dry_run:
        with get_conn() as conn:
            finish_ingest_run(conn, run_id)
            log.info("Finished ingest_run %d", run_id)
    else:
        total = sum(len(rows) for _, _, rows in all_parsed)
        log.info("[DRY RUN] Would have inserted %d rows for %s", total, slug)
