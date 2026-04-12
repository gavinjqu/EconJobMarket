"""Rice University placement page parser.

Rice lists placements in a single table with columns:
Year, Advisor, Student, Initial Placement.

Note: Rice may return 406 with some User-Agent strings.
The scraper's fetch_url uses a browser UA which usually works.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class RiceParser(BasePlacementParser):
    university_slug = "rice"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        idx = 0

        table = soup.find("table")
        if not table:
            log.warning("No table found on Rice placements page")
            return rows

        for tr in table.find_all("tr")[1:]:  # skip header
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            year_text = tds[0].get_text(strip=True)
            raw_name = tds[2].get_text(strip=True) or None
            raw_placement = tds[3].get_text(strip=True) or None

            year = parse_year(year_text)
            if not raw_name:
                continue

            rows.append(
                PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=None,
                    graduation_year=year,
                    row_index=idx,
                )
            )
            idx += 1

        log.info("Parsed %d placement rows from Rice", len(rows))
        return rows
