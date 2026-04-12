import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class TexasAMParser(BasePlacementParser):
    university_slug = "texas_am"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        for el in soup.find_all(["h2", "h3", "h4", "strong", "table"]):
            # Look for year headings like "Class of 2025-2026"
            if el.name in ("h2", "h3", "h4", "strong"):
                text = el.get_text(strip=True)
                m = re.search(r"Class of (\d{4})", text)
                if m:
                    current_year = int(m.group(1))
                else:
                    year = parse_year(text)
                    if year:
                        current_year = year
                continue

            if el.name == "table" and current_year is not None:
                for tr in el.select("tr"):
                    tds = tr.select("td")
                    if not tds:
                        continue
                    if len(tds) >= 2:
                        raw_name = tds[0].get_text(strip=True)
                        raw_placement = tds[1].get_text(strip=True)
                        if not raw_name or raw_name.lower() == "name":
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

        log.info("Parsed %d placement rows from Texas A&M", len(rows))
        return rows
