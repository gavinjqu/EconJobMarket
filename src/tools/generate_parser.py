"""Generate a placement parser for a university using the Claude API.

Fetches the placement page HTML, sends it with a structured prompt to Claude,
writes the generated parser to src/parsers/{slug}.py, and runs a smoke test.

Usage:
    python -m src generate <slug> [--url URL]
"""

import csv
import logging
import pathlib
import sys

import anthropic

from src.utils import fetch_url

log = logging.getLogger(__name__)

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"
_PROMPT_TEMPLATE = _ROOT / "src" / "tools" / "parser_prompt.txt"
_PARSERS_DIR = _ROOT / "src" / "parsers"

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192


def _load_config_row(slug: str) -> dict | None:
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            if row["slug"] == slug:
                return row
    return None


def generate_parser(slug: str, url_override: str | None = None):
    """Generate a parser for the given university slug."""
    config = _load_config_row(slug)
    if config is None:
        log.error("Slug '%s' not found in config/universities.csv", slug)
        sys.exit(1)

    url = url_override or config.get("placement_url", "").strip()
    if not url:
        log.error("No placement URL for '%s'. Use --url to specify.", slug)
        sys.exit(1)

    output_path = _PARSERS_DIR / f"{slug}.py"
    if output_path.exists():
        log.warning("Parser already exists: %s", output_path)
        response = input("Overwrite? [y/N] ").strip().lower()
        if response != "y":
            log.info("Aborted.")
            return

    # Fetch the placement page
    log.info("Fetching %s ...", url)
    try:
        resp = fetch_url(url)
        html = resp.text
    except Exception as e:
        log.error("Failed to fetch %s: %s", url, e)
        sys.exit(1)

    log.info("Fetched %d bytes of HTML", len(html))

    # Build the prompt
    template = _PROMPT_TEMPLATE.read_text()
    prompt = template.format(
        slug=slug,
        name=config["name"],
        url=url,
        html=html[:50000],
    )

    # Call Claude API
    log.info("Sending to Claude API (model=%s) ...", MODEL)
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    code = message.content[0].text

    # Strip markdown fences if the model wrapped them
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first and last lines (fences)
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    # Write the parser
    output_path.write_text(code)
    log.info("Wrote parser to %s", output_path)

    # Run smoke test
    _smoke_test(slug, html, url)


def _smoke_test(slug: str, html: str, url: str):
    """Quick smoke test: import the parser and try parsing the HTML."""
    import importlib

    log.info("Running smoke test ...")
    try:
        mod = importlib.import_module(f"src.parsers.{slug}")
        importlib.reload(mod)  # ensure fresh import

        # Find the parser class
        from src.parsers.base import BasePlacementParser

        parser_cls = None
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if (
                isinstance(obj, type)
                and issubclass(obj, BasePlacementParser)
                and obj is not BasePlacementParser
                and getattr(obj, "university_slug", "") == slug
            ):
                parser_cls = obj
                break

        if parser_cls is None:
            log.error("Smoke test FAILED: no parser class with slug '%s' found", slug)
            return

        parser = parser_cls()
        rows = parser.parse(html, url)
        log.info("Smoke test: parsed %d rows", len(rows))

        if rows:
            sample = rows[0]
            log.info(
                "  First row: name=%s, year=%s, placement=%s",
                sample.raw_name,
                sample.graduation_year,
                sample.raw_placement,
            )
            years = {r.graduation_year for r in rows if r.graduation_year}
            if years:
                log.info("  Year range: %d-%d", min(years), max(years))

        if len(rows) == 0:
            log.warning("Smoke test WARNING: 0 rows parsed — parser may need manual review")

    except Exception as e:
        log.error("Smoke test FAILED: %s", e)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    )
    p = argparse.ArgumentParser()
    p.add_argument("slug")
    p.add_argument("--url", default=None)
    args = p.parse_args()
    generate_parser(args.slug, url_override=args.url)
