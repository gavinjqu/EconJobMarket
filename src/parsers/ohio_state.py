"""Ohio State University placement page parser.

Ohio State lists placements in alternating <p> tags:
- A <p> with just the year (e.g. "2025")
- A <p> with br-separated entries: "- Name - Institution (Position)"
"""

import logging

from bs4 import BeautifulSoup, NavigableString

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class OhioStateParser(BasePlacementParser):
    university_slug = "ohio_state"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Find the intro paragraph, then process subsequent p tags
        intro = None
        for p in soup.find_all("p"):
            if "list below" in p.get_text().lower():
                intro = p
                break

        if not intro:
            log.warning("No intro paragraph found on Ohio State page")
            return rows

        current_year = None
        for p in intro.find_next_siblings("p"):
            text = p.get_text(strip=True)
            if not text:
                continue

            # Check if this is a year marker
            year = parse_year(text)
            if year and len(text) <= 4:
                current_year = year
                continue

            if not current_year:
                continue

            # Extract entries from br-separated content
            for child in p.children:
                if isinstance(child, NavigableString):
                    entry = str(child).strip()
                    if not entry or not entry.startswith("- "):
                        continue

                    entry = entry[2:].strip()
                    # Format: "Name - Institution (Position)"
                    parts = entry.split(" - ", 1)
                    raw_name = parts[0].strip() or None
                    raw_placement = parts[1].strip() if len(parts) > 1 else None

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

        log.info("Parsed %d placement rows from Ohio State", len(rows))
        return rows
