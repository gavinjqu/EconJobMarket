"""Duke University placement page parser.

Duke uses card-based accordion layout: div.card-header has the year,
and each card contains a table with columns: Name, Position, Institution.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class DukeParser(BasePlacementParser):
    university_slug = "duke"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for card_header in soup.find_all("div", class_="card-header"):
            year = parse_year(card_header.get_text(strip=True))
            if not year:
                continue

            card = card_header.parent
            if not card:
                continue

            table = card.find("table")
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:  # skip header
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                raw_position = None
                raw_placement = None

                if len(tds) >= 3:
                    raw_position = tds[1].get_text(strip=True) or None
                    raw_placement = tds[2].get_text(strip=True) or None
                else:
                    raw_placement = tds[1].get_text(strip=True) or None

                if not raw_name:
                    continue

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from Duke", len(rows))
        return rows
