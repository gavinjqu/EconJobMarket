import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCRiversideParser(BasePlacementParser):
    university_slug = "uc_riverside"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        # Structure: single table with <th colspan="2">YEAR</th> rows
        # as year markers, followed by <td> rows for name + placement.
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                # Check for year header row
                th = tr.find("th")
                if th:
                    year = parse_year(th.get_text(strip=True))
                    if year:
                        current_year = year
                    continue

                tds = tr.find_all("td")
                if len(tds) >= 2 and current_year is not None:
                    raw_name = tds[0].get_text(strip=True)
                    raw_placement = tds[1].get_text(strip=True)
                    if not raw_name or raw_name.lower() in ("name", "student"):
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

        log.info("Parsed %d placement rows from UC Riverside", len(rows))
        return rows
