"""UC Irvine placement page parser.

UC Irvine lists all placements in a single table with columns:
Name, Institution, Year.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCIrvineParser(BasePlacementParser):
    university_slug = "uc_irvine"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        table = soup.find("table")
        if not table:
            log.warning("No table found on UC Irvine placements page")
            return rows

        for tr in table.find_all("tr")[1:]:  # skip header
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue

            raw_name = tds[0].get_text(strip=True) or None
            raw_placement = tds[1].get_text(strip=True) or None
            year_text = tds[2].get_text(strip=True)

            year = parse_year(year_text)
            if not raw_name:
                continue

            rows.append(PlacementRow(
                raw_name=raw_name,
                raw_field=None,
                raw_placement=raw_placement,
                raw_position=None,
                graduation_year=year,
                row_index=global_index,
            ))
            global_index += 1

        log.info("Parsed %d placement rows from UC Irvine", len(rows))
        return rows
