import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class ClaremontParser(BasePlacementParser):
    """Claremont Graduate University — placement data is embedded in the
    main PhD Economics program page rather than a dedicated placement page."""

    university_slug = "claremont"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Try tables first
        for table in soup.find_all("table"):
            for tr in table.select("tr"):
                tds = tr.select("td")
                if len(tds) >= 2:
                    raw_name = tds[0].get_text(strip=True)
                    raw_placement = tds[1].get_text(strip=True)
                    if not raw_name or raw_name.lower() in ("name", "student"):
                        continue
                    year = None
                    if len(tds) >= 3:
                        year = parse_year(tds[2].get_text(strip=True))
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

        if rows:
            log.info("Parsed %d placement rows from Claremont", len(rows))
            return rows

        # Fallback: look for alumni/placement section in lists
        current_year = None
        for el in soup.find_all(["h2", "h3", "h4", "ul", "ol"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue
            if el.name in ("ul", "ol"):
                for li in el.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if not text or len(text) < 5:
                        continue
                    parts = re.split(r"\s*[–—,]\s*", text, maxsplit=1)
                    raw_name = parts[0].strip()
                    raw_placement = parts[1].strip() if len(parts) > 1 else None
                    if not raw_name:
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

        log.info("Parsed %d placement rows from Claremont", len(rows))
        return rows
