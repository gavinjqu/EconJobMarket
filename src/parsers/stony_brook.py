import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class StonyBrookParser(BasePlacementParser):
    university_slug = "stony_brook"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for table in soup.find_all("table"):
            for tr in table.select("tr"):
                tds = tr.select("td")
                if len(tds) < 3:
                    continue
                raw_name = tds[0].get_text(strip=True)
                raw_placement = tds[1].get_text(strip=True)
                year_text = tds[2].get_text(strip=True)

                if not raw_name or raw_name.lower() == "name":
                    continue

                year = parse_year(year_text)

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

        log.info("Parsed %d placement rows from Stony Brook", len(rows))
        return rows
