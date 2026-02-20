"""Columbia University placement page parser.

Columbia lists placements by year in <h3> headings followed by <table> elements
with columns: Candidate, Fields, Placement. All years on a single page.
"""

import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class ColumbiaParser(BasePlacementParser):
    university_slug = "columbia"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for h3 in soup.find_all("h3"):
            heading = h3.get_text(strip=True)
            if "Placement" not in heading:
                continue
            year = parse_year(heading)
            if year is None:
                continue

            table = h3.find_next("table")
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:  # skip header row
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                raw_field = tds[1].get_text(strip=True) or None
                raw_placement = tds[2].get_text(strip=True) or None

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

        log.info("Parsed %d placement rows from Columbia", len(rows))
        return rows
