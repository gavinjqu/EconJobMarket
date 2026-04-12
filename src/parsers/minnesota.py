"""University of Minnesota placement page parser.

Minnesota uses accordion buttons with year labels (e.g. "2024-25+")
that control content panels containing tables with columns:
Name, Institution, Position.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class MinnesotaParser(BasePlacementParser):
    university_slug = "minnesota"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for button in soup.find_all("button"):
            btn_classes = " ".join(button.get("class", []))
            if "accordion" not in btn_classes:
                continue

            year = parse_year(button.get_text(strip=True))
            if not year:
                continue

            # Find the target content panel
            target_id = button.get("aria-controls", "")
            if not target_id:
                continue

            panel = soup.find(id=target_id)
            if not panel:
                continue

            table = panel.find("table")
            if not table:
                continue

            for tr in table.find_all("tr")[1:]:  # skip header
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue

                raw_name = tds[0].get_text(strip=True) or None
                raw_placement = tds[1].get_text(strip=True) or None

                if not raw_name:
                    continue

                raw_position = None
                if len(tds) >= 3:
                    raw_position = tds[2].get_text(strip=True) or None

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

        log.info("Parsed %d placement rows from Minnesota", len(rows))
        return rows
