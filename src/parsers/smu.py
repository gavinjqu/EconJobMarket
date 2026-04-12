import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class SMUParser(BasePlacementParser):
    university_slug = "smu"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        # Years as h2 headings, records in tables with 4 columns:
        # Name, Advisor, First job, Current job
        for el in soup.find_all(["h2", "h3", "table"]):
            if el.name in ("h2", "h3"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "table":
                for tr in el.select("tbody tr, tr"):
                    tds = tr.select("td")
                    if not tds:
                        continue
                    raw_name = tds[0].get_text(strip=True)
                    if not raw_name or raw_name.lower() == "name":
                        continue

                    # Column layout: Name, Advisor, First job, Current job
                    raw_placement = None
                    if len(tds) >= 3:
                        raw_placement = tds[2].get_text(strip=True)
                    if not raw_placement and len(tds) >= 4:
                        raw_placement = tds[3].get_text(strip=True)

                    rows.append(PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from SMU", len(rows))
        return rows
