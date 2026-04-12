"""Boston College placement page parser.

Boston College lists alumni in a single large table with columns:
Name, Year, Initial Placement, Current Position.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class BostonCollegeParser(BasePlacementParser):
    university_slug = "bc"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        table = soup.find("table")
        if not table:
            log.warning("No table found on BC placements page")
            return rows

        for tr in table.find_all("tr")[1:]:  # skip header
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            raw_name = tds[0].get_text(strip=True) or None
            year_text = tds[1].get_text(strip=True)
            raw_placement = tds[2].get_text(strip=True) or None

            year = parse_year(year_text)
            if not raw_name:
                continue

            # Fourth column (Current Position) is optional
            raw_position = None
            if len(tds) >= 4:
                raw_position = tds[3].get_text(strip=True) or None

            rows.append(
                PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=year,
                    row_index=global_index,
                )
            )
            global_index += 1

        log.info("Parsed %d placement rows from Boston College", len(rows))
        return rows
