"""University of Maryland placement page parser.

Maryland lists placements by year (h4 headings). For 2025, tables have
single-column category headers (Academic, Federal, Private Sector).
For 2024 and earlier, tables have columns: Name, Job Placement, Area.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class MarylandParser(BasePlacementParser):
    university_slug = "maryland"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "table"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "table":
                trs = el.find_all("tr")
                if not trs:
                    continue

                # Check header to determine format
                header = trs[0]
                header_cells = [
                    c.get_text(strip=True).lower() for c in header.find_all(["th", "td"])
                ]

                if any("name" in h for h in header_cells):
                    # Named columns: Name, Job Placement, Area
                    for tr in trs[1:]:
                        tds = tr.find_all("td")
                        if len(tds) < 2:
                            continue
                        raw_name = tds[0].get_text(strip=True) or None
                        raw_placement = tds[1].get_text(strip=True) or None
                        if not raw_name:
                            continue
                        raw_field = None
                        if len(tds) >= 3:
                            raw_field = tds[2].get_text(strip=True) or None
                        rows.append(
                            PlacementRow(
                                raw_name=raw_name,
                                raw_field=raw_field,
                                raw_placement=raw_placement,
                                raw_position=None,
                                graduation_year=current_year,
                                row_index=global_index,
                            )
                        )
                        global_index += 1
                else:
                    # Category-only format: header is category, rows are placements
                    category = header_cells[0] if header_cells else None
                    for tr in trs[1:]:
                        tds = tr.find_all("td")
                        if not tds:
                            continue
                        raw_placement = tds[0].get_text(strip=True) or None
                        if not raw_placement:
                            continue
                        rows.append(
                            PlacementRow(
                                raw_name=None,
                                raw_field=category,
                                raw_placement=raw_placement,
                                raw_position=None,
                                graduation_year=current_year,
                                row_index=global_index,
                            )
                        )
                        global_index += 1

        log.info("Parsed %d placement rows from Maryland", len(rows))
        return rows
