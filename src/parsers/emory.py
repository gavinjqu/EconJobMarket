"""Emory University placement page parser.

Emory's placement page dynamically loads data from an external CSV file.
The HTML contains a <table> with a data-file attribute pointing to the CSV.
This parser fetches the CSV and parses it directly.

CSV columns: Name, Year Graduated, Initial Placement, Current Placement
"""

import csv
import io
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class EmoryParser(BasePlacementParser):
    university_slug = "emory"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []

        # Find the table element with data-file attribute
        table = soup.find("table", attrs={"data-file": True})
        if not table:
            log.warning("No data-file table found on Emory page")
            return rows

        csv_path = table["data-file"]
        csv_url = urljoin(page_url, csv_path)
        log.info("Fetching Emory CSV from %s", csv_url)

        try:
            resp = requests.get(csv_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            resp.raise_for_status()
        except Exception:
            log.exception("Failed to fetch Emory CSV from %s", csv_url)
            return rows

        reader = csv.DictReader(io.StringIO(resp.text))
        idx = 0
        for record in reader:
            name = record.get("Name", "").strip()
            year_text = record.get("Year Graduated", "")
            placement = record.get("Initial Placement", "").strip()

            if not name:
                continue

            year = parse_year(year_text)

            rows.append(
                PlacementRow(
                    raw_name=name,
                    raw_field=None,
                    raw_placement=placement or None,
                    raw_position=None,
                    graduation_year=year,
                    row_index=idx,
                )
            )
            idx += 1

        log.info("Parsed %d placement rows from Emory", len(rows))
        return rows
