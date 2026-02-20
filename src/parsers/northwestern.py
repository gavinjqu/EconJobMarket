"""Northwestern University placement page parser.

Northwestern lists placements by year with h3 headings, subdivided by sector
(Academic, Government, Private) in h4 headings, with institutions in <ul><li>.
Note: candidate names are not published — only placement destinations.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)

_SECTOR_MAP = {
    "academic": "academic",
    "government": "government",
    "private": "private",
}


class NorthwesternParser(BasePlacementParser):
    university_slug = "northwestern"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for h3 in soup.find_all("h3"):
            year = parse_year(h3.get_text(strip=True))
            if year is None:
                continue

            # Walk siblings until next h3
            current_sector = None
            for sib in h3.find_next_siblings():
                if sib.name == "h3":
                    break

                if sib.name == "div":
                    # Expander div containing h4 + ul
                    for child in sib.children:
                        if not hasattr(child, "name"):
                            continue
                        if child.name == "h4":
                            sector_text = child.get_text(strip=True).lower()
                            current_sector = "academic"
                            for key in _SECTOR_MAP:
                                if key in sector_text:
                                    current_sector = _SECTOR_MAP[key]
                                    break
                        elif child.name == "div":
                            for ul in child.find_all("ul"):
                                for li in ul.find_all("li"):
                                    text = li.get_text(strip=True)
                                    if not text:
                                        continue
                                    rows.append(PlacementRow(
                                        raw_name=f"Northwestern PhD ({year})",
                                        raw_field=None,
                                        raw_placement=text,
                                        raw_position=None,
                                        graduation_year=year,
                                        row_index=global_index,
                                    ))
                                    global_index += 1

        log.info("Parsed %d placement rows from Northwestern (no candidate names)",
                 len(rows))
        return rows
