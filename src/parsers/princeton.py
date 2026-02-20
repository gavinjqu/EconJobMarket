"""Princeton University placement page parser.

Princeton lists placements in a single large table with columns:
Year, Institution, Position/Title, Field. Note: candidate names are
not published on this page.
"""

import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)

_YEAR_RANGE = re.compile(r"(\d{4})\s*[-–]\s*\d{4}")


class PrincetonParser(BasePlacementParser):
    university_slug = "princeton"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        table = soup.find("table")
        if not table:
            log.warning("No table found on Princeton placement page")
            return rows

        for tr in table.find_all("tr")[1:]:  # skip header
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            year_text = tds[0].get_text(strip=True)
            raw_placement = tds[1].get_text(strip=True) or None
            raw_position = tds[2].get_text(strip=True) or None
            raw_field = tds[3].get_text(strip=True) or None

            # Year format: "2024-2025" — use the first year as graduation year
            m = _YEAR_RANGE.match(year_text)
            year = int(m.group(1)) + 1 if m else None  # "2024-2025" → 2025

            if not raw_placement:
                continue

            rows.append(PlacementRow(
                raw_name=f"Princeton PhD ({year_text})",  # no names published
                raw_field=raw_field,
                raw_placement=raw_placement,
                raw_position=raw_position,
                graduation_year=year,
                row_index=global_index,
            ))
            global_index += 1

        log.info("Parsed %d placement rows from Princeton (no candidate names)",
                 len(rows))
        return rows
