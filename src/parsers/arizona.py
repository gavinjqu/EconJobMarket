"""University of Arizona placement page parser.

The page lists placements by year, with each year as a heading element
(<p>, <h3>, or <span> with the year in bold) followed by a table.
Each table row has three cells: Name, Placement, Position.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class ArizonaParser(BasePlacementParser):
    university_slug = "arizona"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[PlacementRow] = []
        global_index = 0

        # Find all tables; determine year by looking at preceding siblings/elements
        for table in soup.find_all("table"):
            year = self._find_year_for_table(table)

            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                if not raw_name:
                    continue

                raw_placement = tds[1].get_text(strip=True) if len(tds) > 1 else None
                raw_placement = raw_placement or None

                raw_position = tds[2].get_text(strip=True) if len(tds) > 2 else None
                raw_position = raw_position or None

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

        log.info("Parsed %d placement rows from Arizona", len(rows))
        return rows

    @staticmethod
    def _find_year_for_table(table) -> int | None:
        """Walk backwards from a table to find the nearest year heading."""
        # Check previous siblings of the table (or its wrapper div)
        node = table
        # If table is inside a div.table-responsive, start from that div
        if (
            table.parent
            and table.parent.name == "div"
            and "table-responsive" in (table.parent.get("class") or [])
        ):
            node = table.parent

        for sibling in _previous_element_siblings(node):
            if sibling.name in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "span"):
                text = sibling.get_text(strip=True)
                year = parse_year(text)
                if year:
                    return year
        return None


def _previous_element_siblings(tag):
    """Yield previous element siblings (skipping NavigableString)."""
    sibling = tag.previous_sibling
    while sibling is not None:
        if hasattr(sibling, "name") and sibling.name is not None:
            yield sibling
        sibling = sibling.previous_sibling
