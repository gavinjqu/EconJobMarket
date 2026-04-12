"""Penn State placement page parser.

Penn State uses Elementor-style jet-toggle accordions.
Each toggle has a year label (div.jet-toggle__control)
and content (div.jet-toggle__content) with alternating
<strong>Name</strong> and <p>Position | Institution</p> entries.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class PennStateParser(BasePlacementParser):
    university_slug = "penn_state"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Find toggle controls (year labels)
        toggles = soup.find_all("div", class_="jet-toggle__control")

        for toggle in toggles:
            year = parse_year(toggle.get_text(strip=True))
            if not year:
                continue

            # Find corresponding content
            content = toggle.find_next_sibling("div", class_="jet-toggle__content")
            if not content:
                continue

            # Content has alternating strong (name) and p (position) tags
            strongs = content.find_all("strong")

            # Build name→placement pairs from strong tags
            # Each strong is a name, the next p (non-name) is placement
            for strong in strongs:
                raw_name = strong.get_text(strip=True) or None
                if not raw_name:
                    continue

                # Find the next p sibling that contains placement info
                raw_placement = None
                next_el = strong.find_next("p")
                if next_el:
                    text = next_el.get_text(strip=True)
                    # Make sure it's not another name (names are in strong tags)
                    if text and not next_el.find("strong"):
                        raw_placement = text

                # Split on " | " if present (format: "Position | Institution")
                raw_position = None
                if raw_placement and " | " in raw_placement:
                    parts = raw_placement.split(" | ", 1)
                    raw_position = parts[0].strip() or None
                    raw_placement = parts[1].strip() or None

                rows.append(
                    PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=raw_position,
                        graduation_year=year,
                        row_index=global_index,
                    )
                )
                global_index += 1

        log.info("Parsed %d placement rows from Penn State", len(rows))
        return rows
