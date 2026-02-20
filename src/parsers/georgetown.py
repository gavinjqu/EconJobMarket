"""Georgetown University placement page parser.

Georgetown lists placements in tables per year with columns:
Ph.D. Student, Job Title, Initial Placement, Thesis Title.
Year headings (h2) precede each table.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class GeorgetownParser(BasePlacementParser):
    university_slug = "georgetown"

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

            if el.name == "table":
                for tr in el.find_all("tr")[1:]:  # skip header
                    tds = tr.find_all("td")
                    if len(tds) < 3:
                        continue

                    raw_name = tds[0].get_text(strip=True) or None
                    raw_position = tds[1].get_text(strip=True) or None
                    raw_placement = tds[2].get_text(strip=True) or None

                    if not raw_name:
                        continue

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=raw_position,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Georgetown", len(rows))
        return rows
