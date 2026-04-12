"""Carnegie Mellon University placement page parser.

CMU Tepper lists placements in multiple tables with columns:
Graduation Year, First Name, Last Name, Hiring Institution / Company.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class CarnegieMellonParser(BasePlacementParser):
    university_slug = "carnegie_mellon"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for table in soup.find_all("table"):
            header_row = table.find("tr")
            if not header_row:
                continue
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]
            if not any("name" in h for h in headers):
                continue

            for tr in table.find_all("tr")[1:]:
                tds = tr.find_all("td")
                if len(tds) < 4:
                    continue

                year_text = tds[0].get_text(strip=True)
                first_name = tds[1].get_text(strip=True)
                last_name = tds[2].get_text(strip=True)
                raw_placement = tds[3].get_text(strip=True) or None

                raw_name = None
                if first_name and last_name:
                    raw_name = f"{first_name} {last_name}"
                elif last_name:
                    raw_name = last_name
                elif first_name:
                    raw_name = first_name

                year = parse_year(year_text)
                if not raw_name:
                    continue

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

        log.info("Parsed %d placement rows from Carnegie Mellon", len(rows))
        return rows
