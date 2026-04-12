"""University of Illinois Urbana-Champaign placement page parser.

UIUC lists placements by year with h2 headings and ul/li entries.
Entries are institution names only (no student names).
Some older data is inside a details/summary accordion.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UIUCParser(BasePlacementParser):
    university_slug = "uiuc"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Collect all relevant elements including those inside details
        all_elements = []
        for el in soup.find_all(["h2", "h3", "h4", "ul", "details"]):
            if el.name == "details":
                for inner in el.find_all(["h2", "h3", "h4", "ul"]):
                    all_elements.append(inner)
            else:
                # Skip elements inside details (handled above)
                if el.find_parent("details"):
                    continue
                all_elements.append(el)

        current_year = None
        for el in all_elements:
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "ul" and current_year:
                for li in el.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if not text:
                        continue

                    # Entries are institution names only (no student names)
                    rows.append(
                        PlacementRow(
                            raw_name=None,
                            raw_field=None,
                            raw_placement=text,
                            raw_position=None,
                            graduation_year=current_year,
                            row_index=global_index,
                        )
                    )
                    global_index += 1

        log.info("Parsed %d placement rows from UIUC (institutions only, no names)", len(rows))
        return rows
