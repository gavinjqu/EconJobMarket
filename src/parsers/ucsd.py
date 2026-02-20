"""UC San Diego placement page parser.

UCSD lists placements in multiple tables (one per year) with columns:
Year, Name, Field, Placement.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCSDParser(BasePlacementParser):
    university_slug = "ucsd"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for table in soup.find_all("table"):
            for tr in table.find_all("tr")[1:]:  # skip header
                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                year_text = tds[0].get_text(strip=True)
                raw_name = tds[1].get_text(strip=True) or None
                raw_field = tds[2].get_text(strip=True) or None
                raw_placement = tds[3].get_text(strip=True) or None

                year = parse_year(year_text)
                if not raw_name:
                    continue

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=raw_field,
                    raw_placement=raw_placement,
                    raw_position=None,
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from UCSD", len(rows))
        return rows
