"""UNC Chapel Hill placement page parser.

UNC lists placements in tables per year with columns:
Name of Graduate, Initial Employer (sometimes with Current Position column).
Year headings (h3) precede each table.
"""

import logging
import re
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UNCParser(BasePlacementParser):
    university_slug = "unc"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "table"]):
            if el.name in ("h2", "h3", "h4"):
                text = el.get_text(strip=True)
                year = parse_year(text)
                if year:
                    current_year = year
                continue

            if el.name == "table":
                for tr in el.find_all("tr")[1:]:  # skip header
                    tds = tr.find_all("td")
                    if len(tds) < 2:
                        continue

                    raw_name = tds[0].get_text(strip=True) or None
                    raw_placement = tds[1].get_text(strip=True) or None

                    if not raw_name:
                        continue

                    raw_position = None
                    if len(tds) >= 3:
                        raw_position = tds[2].get_text(strip=True) or None

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=raw_position,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from UNC", len(rows))
        return rows
