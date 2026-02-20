"""University of Rochester placement page parser.

Rochester lists placements in <details>/<summary> accordions by year,
each containing a <table> with columns: Name, Institution, Title.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class RochesterParser(BasePlacementParser):
    university_slug = "rochester"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for details in soup.find_all("details"):
            summary = details.find("summary")
            if not summary:
                continue
            year = parse_year(summary.get_text(strip=True))
            if year is None:
                continue

            table = details.find("table")
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:  # skip header row
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                raw_placement = tds[1].get_text(strip=True) or None
                raw_position = tds[2].get_text(strip=True) or None

                if not raw_name:
                    continue

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from Rochester", len(rows))
        return rows
