"""Arizona State University placement page parser.

ASU lists placements in multiple tables. The first row of each table
has the year in the first cell. Data rows have: Name, 1st Year Placement.
Some tables have a third column for Current Position.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class ArizonaStateParser(BasePlacementParser):
    university_slug = "arizona_state"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for table in soup.find_all("table"):
            trs = table.find_all("tr")
            if not trs:
                continue

            # First row has year in first cell
            header = trs[0]
            header_cells = [c.get_text(strip=True) for c in header.find_all(["th", "td"])]
            year = parse_year(header_cells[0]) if header_cells else None

            for tr in trs[1:]:
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
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from Arizona State", len(rows))
        return rows
