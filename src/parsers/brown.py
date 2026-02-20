"""Brown University placement page parser.

Brown lists placements as paragraphs in format: "Name-Institution, Position"
or "Name -Institution, Position".
"""

import logging
import re
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class BrownParser(BasePlacementParser):
    university_slug = "brown"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "p"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            text = el.get_text(strip=True)
            if not text:
                continue

            # Check if this looks like a placement entry: "Name-Institution"
            match = re.match(r'^([A-Z][^-–—]+?)\s*[-–—]\s*(.+)$', text)
            if not match:
                continue

            raw_name = match.group(1).strip()
            raw_placement = match.group(2).strip()

            if not raw_name or len(raw_name) < 3:
                continue

            # Skip nav/footer text
            if any(kw in raw_name.lower() for kw in ['brown university', 'department', 'copyright']):
                continue

            rows.append(PlacementRow(
                raw_name=raw_name,
                raw_field=None,
                raw_placement=raw_placement or None,
                raw_position=None,
                graduation_year=current_year,
                row_index=global_index,
            ))
            global_index += 1

        log.info("Parsed %d placement rows from Brown", len(rows))
        return rows
