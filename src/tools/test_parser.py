"""Test harness for validating generated parsers.

Fetches the live page, runs the parser, and reports statistics.

Usage:
    python -m src.tools.test_parser <slug> [--url URL]
"""

import csv
import importlib
import logging
import pathlib
import sys

from src.parsers.base import BasePlacementParser
from src.utils import fetch_url

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"


def _load_config_row(slug: str) -> dict | None:
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            if row["slug"] == slug:
                return row
    return None


def _find_parser(slug: str) -> type[BasePlacementParser] | None:
    """Import and find the parser class for a slug."""
    try:
        mod = importlib.import_module(f"src.parsers.{slug}")
        importlib.reload(mod)
    except ImportError as e:
        log.error("Cannot import parser module for '%s': %s", slug, e)
        return None

    for attr in dir(mod):
        obj = getattr(mod, attr)
        if (
            isinstance(obj, type)
            and issubclass(obj, BasePlacementParser)
            and obj is not BasePlacementParser
            and getattr(obj, "university_slug", "") == slug
        ):
            return obj
    return None


def test_parser(slug: str, url_override: str | None = None):
    """Fetch the live page, run the parser, report stats."""
    config = _load_config_row(slug)
    if config is None:
        log.error("Slug '%s' not found in config", slug)
        sys.exit(1)

    url = url_override or config.get("placement_url", "").strip()
    if not url:
        log.error("No URL for '%s'", slug)
        sys.exit(1)

    parser_cls = _find_parser(slug)
    if parser_cls is None:
        log.error("No parser found for '%s'", slug)
        sys.exit(1)

    parser = parser_cls()

    # Fetch all pages (following pagination)
    all_rows = []
    current_url = url
    page_num = 0

    while current_url:
        page_num += 1
        log.info("Fetching page %d: %s", page_num, current_url)

        try:
            resp = fetch_url(current_url)
            html = resp.text
        except Exception as e:
            log.error("Fetch failed: %s", e)
            break

        try:
            rows = parser.parse(html, current_url)
        except Exception as e:
            log.error("Parse failed: %s", e)
            break

        all_rows.extend(rows)
        log.info("  Page %d: %d rows", page_num, len(rows))

        current_url = parser.get_next_page_url(html, current_url)

    # Report
    print()
    print(f"=== Test Report: {slug} ({config['name']}) ===")
    print(f"URL:        {url}")
    print(f"Pages:      {page_num}")
    print(f"Total rows: {len(all_rows)}")

    if not all_rows:
        print("STATUS: FAIL — no rows parsed")
        return

    years = sorted({r.graduation_year for r in all_rows if r.graduation_year})
    if years:
        print(f"Year range: {min(years)}–{max(years)}")
    else:
        print("Year range: none found")

    fields_present = sum(1 for r in all_rows if r.raw_field)
    placements_present = sum(1 for r in all_rows if r.raw_placement)
    positions_present = sum(1 for r in all_rows if r.raw_position)

    print(f"Fields:     {fields_present}/{len(all_rows)} rows have field data")
    print(f"Placements: {placements_present}/{len(all_rows)} rows have placement data")
    print(f"Positions:  {positions_present}/{len(all_rows)} rows have position data")

    # Show sample rows
    print(f"\nSample rows (first 5):")
    for r in all_rows[:5]:
        print(f"  [{r.graduation_year}] {r.raw_name} → {r.raw_placement}"
              f"{(' (' + r.raw_position + ')') if r.raw_position else ''}")

    # Check for common issues
    issues = []
    if len(all_rows) < 10:
        issues.append(f"Very few rows ({len(all_rows)}) — parser may be incomplete")
    names_empty = sum(1 for r in all_rows if not r.raw_name or not r.raw_name.strip())
    if names_empty:
        issues.append(f"{names_empty} rows with empty names")
    if not years:
        issues.append("No graduation years found")
    if placements_present < len(all_rows) * 0.5:
        issues.append(f"Only {placements_present}/{len(all_rows)} rows have placement data")

    if issues:
        print("\nWarnings:")
        for issue in issues:
            print(f"  ⚠ {issue}")
        print("\nSTATUS: REVIEW NEEDED")
    else:
        print("\nSTATUS: PASS")


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("slug")
    p.add_argument("--url", default=None)
    args = p.parse_args()
    test_parser(args.slug, url_override=args.url)
