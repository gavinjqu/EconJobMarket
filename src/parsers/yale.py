"""Yale University placement page parser.

Yale lists placements by year with h2/h3 headings (e.g. "2024-25"),
followed by multiple 2-column tables: Name (bold), Placement.
"""

import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)

_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–]\s*\d{2,4}")


class YaleParser(BasePlacementParser):
    university_slug = "yale"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "table"]):
            if el.name in ("h2", "h3", "h4"):
                m = _YEAR_RANGE.search(el.get_text(strip=True))
                if m:
                    current_year = int(m.group(1)) + 1  # "2024-25" → 2025
                continue

            if el.name == "table" and current_year:
                for tr in el.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) < 2:
                        continue

                    raw_name = tds[0].get_text(strip=True) or None
                    raw_placement = tds[1].get_text(strip=True) or None

                    if not raw_name:
                        continue

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Yale", len(rows))
        return rows
