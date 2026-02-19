"""CLI entry point: python -m src <university>"""
import argparse
import logging

from src.scraper import run_scraper


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Econ PhD Placement Scraper",
    )
    parser.add_argument(
        "university",
        choices=["harvard", "stanford", "all"],
        help="Which university to scrape, or 'all'",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse but do not write to database",
    )
    args = parser.parse_args()
    run_scraper(args.university, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
