"""University of Virginia placement page parser.

UVA lists placements by year (h3 headings) followed by div blocks
for each person containing nested divs:
  - Name div
  - "Initial Placement: ..." div
  - "Thesis: ..." div
"""

import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UVAParser(BasePlacementParser):
    university_slug = "uva"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4"]):
            text = el.get_text(strip=True)
            year = parse_year(text)
            if not year:
                continue
            # Only use pure year headings (not "Quicklink..." etc.)
            if not re.match(r"^\d{4}$", text.strip()):
                continue
            current_year = year

            # Process sibling divs until next heading
            for sib in el.find_next_siblings():
                if sib.name in ("h2", "h3", "h4"):
                    break
                if sib.name != "div":
                    continue

                full_text = sib.get_text(strip=True)
                if not full_text or len(full_text) < 5:
                    continue

                # Extract name and placement from nested divs
                inner_divs = sib.find_all("div", recursive=True)
                if not inner_divs:
                    continue

                raw_name = None
                raw_placement = None

                for div in inner_divs:
                    div_text = div.get_text(strip=True)
                    if div_text.startswith("Initial Placement:"):
                        raw_placement = (
                            div_text.replace("Initial Placement:", "", 1).strip() or None
                        )
                    elif div_text.startswith("Thesis:"):
                        continue
                    elif (
                        not raw_name
                        and div_text
                        and not div_text.startswith("Initial")
                        and not div_text.startswith("Thesis")
                    ):
                        # First non-label div is the name
                        raw_name = div_text

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

        log.info("Parsed %d placement rows from UVA", len(rows))
        return rows
