"""UCLA Economics placement page parser.

UCLA lists placements by year with h-tag headings (e.g. "2025"),
followed by 2-column tables: Name, Placement (institution + position).
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCLAParser(BasePlacementParser):
    university_slug = "ucla"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "h5", "table"]):
            if el.name in ("h2", "h3", "h4", "h5"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
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

        log.info("Parsed %d placement rows from UCLA", len(rows))
        return rows
