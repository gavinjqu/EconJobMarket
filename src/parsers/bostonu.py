"""Boston University placement page parser.

BU lists placements by year (h3 headings) with tables where columns are
[Placement, Name] (inverted order).
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class BostonUParser(BasePlacementParser):
    university_slug = "bostonu"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "table"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "table" and current_year:
                for tr in el.find_all("tr"):
                    tds = tr.find_all("td")
                    if len(tds) < 2:
                        continue

                    # Columns are [Placement, Name] (inverted)
                    raw_placement = tds[0].get_text(strip=True) or None
                    raw_name = tds[1].get_text(strip=True) or None

                    if not raw_name:
                        continue

                    rows.append(
                        PlacementRow(
                            raw_name=raw_name,
                            raw_field=None,
                            raw_placement=raw_placement,
                            raw_position=None,
                            graduation_year=current_year,
                            row_index=global_index,
                        )
                    )
                    global_index += 1

        log.info("Parsed %d placement rows from Boston University", len(rows))
        return rows
