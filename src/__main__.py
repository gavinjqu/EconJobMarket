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


def _parse_set_args(pairs: list[str]) -> dict:
    """Parse repeated --set field=value arguments. 'null' clears a field."""
    changes = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--set expects field=value, got: {pair}")
        field, _, value = pair.partition("=")
        field = field.strip()
        value = value.strip()
        if value.lower() == "null" or value == "":
            changes[field] = None
        elif field in ("graduation_year", "is_postdoc"):
            changes[field] = int(value)
        else:
            changes[field] = value
    return changes


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
        "program",
        help="Program slug or 'all' (default programs use the university slug)",
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

    # --- init-db / migrate (same runner; two names for the two intents) ---
    sub.add_parser("init-db", help="Create the database and apply all migrations")
    sub.add_parser("migrate", help="Apply pending schema migrations (backs up first)")

    # --- seed-programs ---
    sub.add_parser(
        "seed-programs",
        help="Idempotently load named programs + pages from config/programs.csv",
    )

    # --- placement (curation) ---
    sp_placement = sub.add_parser("placement", help="Curate core placement rows")
    placement_sub = sp_placement.add_subparsers(dest="placement_command", required=True)
    sp_edit = placement_sub.add_parser(
        "edit",
        help="Correct a placement row; sets human_locked so scrapes can't clobber it",
    )
    sp_edit.add_argument("placement_id", type=int)
    sp_edit.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="Field to change (repeatable). Use value 'null' to clear.",
    )
    sp_edit.add_argument(
        "--unlock",
        action="store_true",
        help="Clear human_locked so scrape upserts may update the row again",
    )

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
        slug = args.program
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

    elif args.command in ("init-db", "migrate"):
        from src.database import init_db

        init_db()
        log.info("Database is at the current schema version (data/placements.db)")

    elif args.command == "seed-programs":
        from src.database import get_conn, seed_programs

        with get_conn() as conn:
            created, pages = seed_programs(conn)
        log.info("Seeded %d new programs and %d new pages", created, pages)

    elif args.command == "placement":
        from src.database import edit_placement, get_conn

        changes = _parse_set_args(args.set)
        with get_conn() as conn:
            before, after = edit_placement(conn, args.placement_id, changes, unlock=args.unlock)
        for field in sorted(set(changes) | {"human_locked"}):
            log.info(
                "placement %d: %s: %r -> %r",
                args.placement_id,
                field,
                before.get(field),
                after.get(field),
            )

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
