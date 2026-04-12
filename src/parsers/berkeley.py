"""UC Berkeley placement page parser.

Berkeley lists placements by year with h3 headings, then sector labels
in <p> tags, followed by <ul><li> entries with "Institution; Position" format.
Note: candidate names are not published — only institution and position.
"""

import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)

_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–]\s*\d{4}")


class BerkeleyParser(BasePlacementParser):
    university_slug = "berkeley"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for h in soup.find_all(["h2", "h3", "h4"]):
            m = _YEAR_RANGE.search(h.get_text(strip=True))
            if not m:
                continue
            current_year = int(m.group(1)) + 1  # "2024-2025" → 2025

            for sib in h.find_next_siblings():
                if sib.name in ("h2", "h3") and _YEAR_RANGE.search(sib.get_text("")):
                    break

                if sib.name == "ul":
                    for li in sib.find_all("li"):
                        text = li.get_text(strip=True)
                        if not text:
                            continue

                        # Format: "Institution; Position"
                        if ";" in text:
                            parts = text.split(";", 1)
                            raw_placement = parts[0].strip()
                            raw_position = parts[1].strip()
                        else:
                            raw_placement = text
                            raw_position = None

                        rows.append(
                            PlacementRow(
                                raw_name=f"Berkeley PhD ({current_year})",
                                raw_field=None,
                                raw_placement=raw_placement,
                                raw_position=raw_position,
                                graduation_year=current_year,
                                row_index=global_index,
                            )
                        )
                        global_index += 1

        log.info("Parsed %d placement rows from Berkeley (no candidate names)", len(rows))
        return rows
