"""University of Florida placement page parser.

Florida lists alumni by year with h3 headings, followed by <ul> with
<li> containing bold name and placement text.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class FloridaParser(BasePlacementParser):
    university_slug = "florida"

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
                    # Name is in <b>, <strong>, or <a><strong>
                    name_el = li.find(["b", "strong"])
                    if name_el:
                        raw_name = name_el.get_text(strip=True)
                    else:
                        continue

                    if not raw_name:
                        continue

                    # Placement is the remaining text after the name
                    full_text = li.get_text(strip=True)
                    # Remove the name from the full text to get placement
                    raw_placement = full_text.replace(raw_name, "", 1).strip()
                    # Clean leading/trailing punctuation
                    raw_placement = raw_placement.strip(",;– ") or None

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Florida", len(rows))
        return rows
