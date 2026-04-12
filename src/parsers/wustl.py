"""Washington University in St. Louis placement page parser.

WUSTL has a PhD Placement History section with year markers in
<strong> tags inside <p> tags, followed by <ul><li> entries:
"Name, Institution".
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class WUSTLParser(BasePlacementParser):
    university_slug = "wustl"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Find the PhD Placement History section
        h2 = soup.find("h2", string=lambda s: s and "PhD Placement History" in s)
        if not h2:
            log.warning("No PhD Placement History section found on WUSTL page")
            return rows

        # Content is in the div following the h2
        container = h2.find_next_sibling("div")
        if not container:
            log.warning("No content div found after WUSTL placement heading")
            return rows

        current_year = None
        for el in container.find_all(["p", "ul"]):
            if el.name == "p":
                strong = el.find("strong")
                if strong:
                    year = parse_year(strong.get_text(strip=True))
                    if year:
                        current_year = year
                continue

            if el.name == "ul" and current_year:
                for li in el.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if not text:
                        continue

                    # Format: "Name, Institution"
                    parts = text.split(",", 1)
                    raw_name = parts[0].strip() or None
                    raw_placement = parts[1].strip().strip(",; ") if len(parts) > 1 else None

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

        log.info("Parsed %d placement rows from WUSTL", len(rows))
        return rows
