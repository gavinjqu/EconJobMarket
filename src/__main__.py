"""CLI entry point: python -m src <command> [args]"""

import argparse
import csv
import logging
import pathlib

from src.parsers import PARSERS
from src.scraper import run_scraper

log = logging.getLogger(__name__)

_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "universities.csv"


def _load_config_slugs():
    """Return set of slugs from config/universities.csv."""
    slugs = set()
    if _CONFIG.exists():
        with open(_CONFIG, newline="") as f:
            for row in csv.DictReader(f):
                slugs.add(row["slug"])
    return slugs


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Econ PhD Placement Scraper & Importer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- scrape ---
    sp_scrape = sub.add_parser("scrape", help="Scrape placement data")
    sp_scrape.add_argument(
        "university",
        help="University slug or 'all'",
    )
    sp_scrape.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but do not write to database",
    )

    # --- import ---
    sp_import = sub.add_parser("import", help="Import external data")
    sp_import.add_argument(
        "source",
        choices=["econphdplacements", "gap-report"],
        help="Data source to import, or 'gap-report'",
    )
    sp_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without DB writes",
    )

    # --- init-db ---
    sub.add_parser("init-db", help="Initialize SQLite database and seed data")

    # --- generate ---
    sp_gen = sub.add_parser("generate", help="Generate a parser via LLM")
    sp_gen.add_argument(
        "university",
        help="University slug to generate parser for",
    )
    sp_gen.add_argument(
        "--url",
        default=None,
        help="Override placement page URL",
    )
    sp_gen.add_argument(
        "--batch",
        action="store_true",
        help="Generate parsers for all uncovered schools",
    )

    args = parser.parse_args()

    if args.command == "scrape":
        slug = args.university
        if slug != "all" and slug not in PARSERS:
            parser.error(
                f"Unknown parser '{slug}'. Available: {', '.join(sorted(PARSERS))} or 'all'"
            )
        run_scraper(slug, dry_run=args.dry_run)

    elif args.command == "import":
        if args.source == "econphdplacements":
            from src.importers.econphdplacements import run_import

            run_import(dry_run=args.dry_run)
        elif args.source == "gap-report":
            from src.importers.gap_report import run_gap_report

            run_gap_report()

    elif args.command == "init-db":
        from src.database import init_db

        init_db()
        log.info("Database initialized at data/placements.db")

    elif args.command == "generate":
        if args.batch:
            from src.tools.batch_generate import run_batch

            run_batch()
        else:
            config_slugs = _load_config_slugs()
            if args.university not in config_slugs:
                parser.error(
                    f"Unknown university '{args.university}'. Must be in config/universities.csv"
                )
            from src.tools.generate_parser import generate_parser

            generate_parser(args.university, url_override=args.url)


if __name__ == "__main__":
    main()
