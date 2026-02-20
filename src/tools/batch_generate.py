"""Batch-generate parsers for all uncovered schools.

Iterates through config/universities.csv, skips schools that already have
parsers, and runs the LLM parser generator + smoke test for each.

Usage:
    python -m src generate --batch <ignored_slug>
    python -m src.tools.batch_generate
"""

import csv
import logging
import pathlib

from src.parsers import PARSERS
from src.tools.generate_parser import generate_parser

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"
_PARSERS_DIR = _ROOT / "src" / "parsers"


def run_batch():
    with open(_CONFIG, newline="") as f:
        rows = list(csv.DictReader(f))

    existing = set(PARSERS.keys())
    results = {"generated": [], "skipped": [], "failed": []}

    for row in rows:
        slug = row["slug"]
        url = row.get("placement_url", "").strip()

        if slug in existing:
            results["skipped"].append(slug)
            continue

        parser_file = _PARSERS_DIR / f"{slug}.py"
        if parser_file.exists():
            results["skipped"].append(slug)
            continue

        if not url:
            log.warning("No placement URL for '%s' — skipping", slug)
            results["failed"].append((slug, "no URL"))
            continue

        log.info("=== Generating parser for: %s ===", slug)
        try:
            generate_parser(slug, url_override=url)
            results["generated"].append(slug)
        except Exception as e:
            log.error("Failed to generate parser for '%s': %s", slug, e)
            results["failed"].append((slug, str(e)))

    # Summary
    print("\n=== Batch Generation Summary ===")
    print(f"Generated: {len(results['generated'])}")
    for s in results["generated"]:
        print(f"  + {s}")
    print(f"Skipped (already exists): {len(results['skipped'])}")
    print(f"Failed: {len(results['failed'])}")
    for s, reason in results["failed"]:
        print(f"  - {s}: {reason}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    run_batch()
