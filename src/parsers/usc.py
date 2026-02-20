"""USC placement page parser.

USC uses accordion panels with year headers. Each panel contains
entries with Name followed by "Position: ..." and "Institution: ..."
paragraphs separated by dashes.
"""

import logging
import re
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class USCParser(BasePlacementParser):
    university_slug = "usc"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        panels = soup.find_all("div", class_="accordion-panel")

        for panel in panels:
            # Find year from preceding button/header
            parent = panel.parent
            year = None
            if parent:
                btn = parent.find_previous("button")
                if btn:
                    year = parse_year(btn.get_text(strip=True))

            # Parse entries: text has "Name, LastPosition: XInstitution: Y"
            # Split by the dash separator "–"
            text = panel.get_text(separator="\n", strip=True)
            entries = re.split(r"\n*–\n*", text)

            for entry in entries:
                entry = entry.strip()
                if not entry:
                    continue

                lines = entry.split("\n")
                raw_name = None
                raw_position = None
                raw_placement = None

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("Position:"):
                        raw_position = line.replace("Position:", "", 1).strip() or None
                    elif line.startswith("Institution:"):
                        raw_placement = line.replace("Institution:", "", 1).strip() or None
                    elif not raw_name:
                        # First line is the name (e.g. "Last, First")
                        raw_name = line

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

        log.info("Parsed %d placement rows from USC", len(rows))
        return rows
