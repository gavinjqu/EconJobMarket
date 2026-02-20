"""University of Notre Dame placement page parser.

Notre Dame lists placements by year (h2 headings) followed by
ul/li entries in format: "Name, Placement".
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class NotreDameParser(BasePlacementParser):
    university_slug = "notre_dame"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "ul"]):
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

                    # Format: "Name, Placement, More info"
                    # Split on first comma to separate name from placement
                    parts = text.split(",", 1)
                    raw_name = parts[0].strip() or None
                    raw_placement = parts[1].strip().strip(",; ") if len(parts) > 1 else None

                    if not raw_name:
                        continue

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Notre Dame", len(rows))
        return rows
