"""Indiana University placement page parser.

Indiana lists placements by year (h3 headings) followed by ul/li entries
in format: 'Name, Institution, "Thesis Title," Chair: X, Year'.
"""

import logging
import re
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class IndianaParser(BasePlacementParser):
    university_slug = "indiana"

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

                    # Format: "Name, Institution, "Thesis", Chair: X, Year"
                    # Split on first comma to get name
                    parts = text.split(",", 1)
                    raw_name = parts[0].strip() or None

                    if not raw_name:
                        continue

                    # Get placement (second part before thesis quote)
                    raw_placement = None
                    if len(parts) > 1:
                        remainder = parts[1].strip()
                        # Try to extract institution before the thesis title
                        quote_match = re.search(r'["\u201c]', remainder)
                        if quote_match:
                            raw_placement = remainder[:quote_match.start()].strip().strip(",; ") or None
                        else:
                            # No thesis - take up to "Chair:" if present
                            chair_match = re.search(r',?\s*Chair:', remainder, re.IGNORECASE)
                            if chair_match:
                                raw_placement = remainder[:chair_match.start()].strip().strip(",; ") or None
                            else:
                                raw_placement = remainder.strip().strip(",; ") or None

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Indiana", len(rows))
        return rows
