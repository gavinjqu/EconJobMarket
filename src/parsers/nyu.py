"""NYU Economics placement page parser.

NYU lists placements in <details>/<summary> accordions by year.
Each section contains <p> tags with institutions separated by <br>.
Note: candidate names are not published — only placement destinations.
"""

import re
import logging
from bs4 import BeautifulSoup, NavigableString
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)

_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–]\s*(\d{4})")


class NYUParser(BasePlacementParser):
    university_slug = "nyu"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for details in soup.find_all("details"):
            summary = details.find("summary")
            if not summary:
                continue
            summary_text = summary.get_text(strip=True)
            m = _YEAR_RANGE.search(summary_text)
            year = int(m.group(2)) if m else None  # "2024 - 2025" → 2025

            # Placements are in <p> tags, separated by <br>
            for p in details.find_all("p"):
                # Split on <br> tags to get individual placements
                lines = []
                for child in p.children:
                    if isinstance(child, NavigableString):
                        text = child.strip()
                        if text:
                            lines.append(text)
                    elif child.name == "br":
                        continue
                    elif child.name:
                        text = child.get_text(strip=True)
                        if text:
                            lines.append(text)

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    rows.append(PlacementRow(
                        raw_name=f"NYU PhD ({summary_text})",  # no names published
                        raw_field=None,
                        raw_placement=line,
                        raw_position=None,
                        graduation_year=year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from NYU (no candidate names)",
                 len(rows))
        return rows
