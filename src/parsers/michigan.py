"""University of Michigan placement page parser.

Michigan uses accordion sections with h3 year headings (e.g.
"2024-2025 Job Market Placements") followed by div.accordion-body
containing <p><b>Name</b><br/>Placement</p> entries.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class MichiganParser(BasePlacementParser):
    university_slug = "michigan"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for h3 in soup.find_all("h3"):
            text = h3.get_text(strip=True)
            if "Job Market" not in text and "Placement" not in text:
                continue

            year = parse_year(text)
            if not year:
                continue

            # Find the accordion body after this heading
            body_div = h3.find_next("div", class_="accordion-body")
            if not body_div:
                continue

            for p in body_div.find_all("p"):
                bold = p.find(["b", "strong"])
                if not bold:
                    continue

                raw_name = bold.get_text(strip=True) or None
                if not raw_name:
                    continue

                # Placement is the text after the name (after br)
                full_text = p.get_text(strip=True)
                raw_placement = full_text.replace(raw_name, "", 1).strip()
                raw_placement = raw_placement.strip(",;– ") or None

                rows.append(
                    PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=year,
                        row_index=global_index,
                    )
                )
                global_index += 1

        log.info("Parsed %d placement rows from Michigan", len(rows))
        return rows
