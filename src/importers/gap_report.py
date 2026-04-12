"""Report coverage gaps across the 50 target schools.

Shows which schools have data, row counts, year ranges, and which
still need scrapers or import.

Usage:
    python -m src import gap-report
"""

import csv
import logging
import pathlib

from src.database import get_conn
from src.parsers import PARSERS

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"


def _load_config() -> list[dict]:
    with open(_CONFIG, newline="") as f:
        return list(csv.DictReader(f))


def run_gap_report():
    config = _load_config()

    # Query current placement counts from the database
    try:
        with get_conn() as conn:
            rows = conn.execute("""
                SELECT u.name,
                       COUNT(p.placement_id) AS cnt,
                       MIN(p.graduation_year) AS min_year,
                       MAX(p.graduation_year) AS max_year
                FROM source_university u
                LEFT JOIN placement p ON p.university_id = u.university_id
                GROUP BY u.university_id, u.name
                ORDER BY cnt DESC
            """).fetchall()
            db_stats = {row[0]: (row[1], row[2], row[3]) for row in rows}
    except Exception as e:
        log.warning("Could not query database: %s. Showing config-only report.", e)
        db_stats = {}

    parser_slugs = set(PARSERS.keys())

    print()
    print(f"{'School':<50} {'Rows':>6} {'Years':>12} {'Parser':>8} {'Import':>8}")
    print("-" * 90)

    total_rows = 0
    covered = 0
    need_work = []

    for row in config:
        slug = row["slug"]
        name = row["name"]
        in_ext = row.get("in_external_dataset", "no").strip().lower() == "yes"
        has_parser = slug in parser_slugs

        cnt, min_y, max_y = db_stats.get(name, (0, None, None))
        total_rows += cnt

        year_range = f"{min_y}-{max_y}" if min_y else ""
        parser_flag = "yes" if has_parser else ""
        import_flag = "yes" if in_ext else ""

        if cnt > 0:
            covered += 1
        else:
            need_work.append(slug)

        print(f"{name:<50} {cnt:>6} {year_range:>12} {parser_flag:>8} {import_flag:>8}")

    print("-" * 90)
    print(f"Total: {total_rows} placements across {covered}/{len(config)} schools")
    if need_work:
        print(f"\nSchools needing data ({len(need_work)}):")
        for slug in need_work:
            print(f"  - {slug}")
    print()
