"""University of Oregon placement page parser.

Oregon uses h2 headers for year sections (e.g., "2024-25 PhD Placements")
followed by h3 student names and ul/li lists with metadata including:
  - Initial Placement
  - Fields
  - Job Market Paper / Dissertation
  - Committee
"""

import logging
import re
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class OregonParser(BasePlacementParser):
    university_slug = "oregon"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        idx = 0
        current_year = None

        for tag in soup.find_all(["h2", "h3"]):
            if tag.name == "h2":
                text = tag.get_text(strip=True)
                # Match patterns like "2024-25 PhD Placements" or "2022-23"
                m = re.search(r"(20\d{2})", text)
                if m:
                    current_year = int(m.group(1))
                continue

            if tag.name == "h3" and current_year:
                name = tag.get_text(strip=True)
                if not name:
                    continue

                # Look for the following <ul> with metadata
                ul = tag.find_next_sibling("ul")
                placement = None
                field = None

                if ul:
                    for li in ul.find_all("li"):
                        text = li.get_text(strip=True)
                        if text.lower().startswith("initial placement:"):
                            placement = text.split(":", 1)[1].strip()
                        elif text.lower().startswith("fields:"):
                            field = text.split(":", 1)[1].strip()

                rows.append(PlacementRow(
                    raw_name=name,
                    raw_field=field,
                    raw_placement=placement,
                    raw_position=None,
                    graduation_year=current_year,
                    row_index=idx,
                ))
                idx += 1

        log.info("Parsed %d placement rows from Oregon", len(rows))
        return rows
