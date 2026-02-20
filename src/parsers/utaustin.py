"""UT Austin placement page parser.

UT Austin uses accordion items (li.accordion-item) with year headers
(a.accordion-title with "2024-2025: 10 Graduates") containing tables
with columns: Name, Dissertation Title, Supervisor, First Position,
Current Position.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UTAustinParser(BasePlacementParser):
    university_slug = "utaustin"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for item in soup.find_all("li", class_="accordion-item"):
            # Get year from accordion title
            title = item.find("a", class_="accordion-title")
            if not title:
                continue

            year = parse_year(title.get_text(strip=True))
            if not year:
                continue

            table = item.find("table")
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:  # skip header
                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                # tds[1] = Dissertation Title (skip)
                # tds[2] = Supervisor (skip)
                raw_placement = tds[3].get_text(strip=True) or None

                if not raw_name:
                    continue

                raw_position = None
                if len(tds) >= 5:
                    raw_position = tds[4].get_text(strip=True) or None

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from UT Austin", len(rows))
        return rows
