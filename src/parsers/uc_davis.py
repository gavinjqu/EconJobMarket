"""UC Davis placement page parser.

UC Davis lists all placements in a single table with columns:
Last Name, First Name, PhD Date, First Placement, First Job Title.
PhD Date is in "Mon-YY" format (e.g. "Jun-25").
"""

import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


def _parse_mon_yy(text):
    """Parse 'Mon-YY' format to a 4-digit year."""
    if not text:
        return None
    m = re.search(r"(\d{2})$", text.strip())
    if m:
        yy = int(m.group(1))
        return 2000 + yy if yy < 80 else 1900 + yy
    return None


class UCDavisParser(BasePlacementParser):
    university_slug = "uc_davis"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        table = soup.find("table")
        if not table:
            log.warning("No table found on UC Davis placements page")
            return rows

        for tr in table.find_all("tr")[1:]:  # skip header
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue

            last_name = tds[0].get_text(strip=True)
            first_name = tds[1].get_text(strip=True)
            year_text = tds[2].get_text(strip=True)
            raw_placement = tds[3].get_text(strip=True) or None

            raw_name = None
            if last_name and first_name:
                raw_name = f"{first_name} {last_name}"
            elif last_name:
                raw_name = last_name

            year = _parse_mon_yy(year_text)
            if not raw_name:
                continue

            raw_position = None
            if len(tds) >= 5:
                raw_position = tds[4].get_text(strip=True) or None

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

        log.info("Parsed %d placement rows from UC Davis", len(rows))
        return rows
