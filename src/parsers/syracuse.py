import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class SyracuseParser(BasePlacementParser):
    """Syracuse placement data is primarily in a PDF.

    This parser extracts what limited placement info is available
    from the HTML page text.
    """
    university_slug = "syracuse"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # The page mentions placements inline. Try to find any structured
        # placement data in tables or lists.
        for table in soup.find_all("table"):
            current_year = None
            for tr in table.select("tr"):
                tds = tr.select("td")
                if not tds:
                    continue
                if len(tds) >= 2:
                    raw_name = tds[0].get_text(strip=True)
                    raw_placement = tds[1].get_text(strip=True)
                    if not raw_name or raw_name.lower() == "name":
                        continue
                    year = None
                    if len(tds) >= 3:
                        year = parse_year(tds[2].get_text(strip=True))
                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=year,
                        row_index=global_index,
                    ))
                    global_index += 1

        if not rows:
            log.warning("Syracuse placement data is primarily in a PDF — "
                        "0 rows parsed from HTML")
        else:
            log.info("Parsed %d placement rows from Syracuse", len(rows))
        return rows
