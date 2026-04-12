import re
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class FloridaStateParser(BasePlacementParser):
    university_slug = "florida_state"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        for el in soup.find_all(["h2", "h3", "h4", "table", "ul", "ol"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "table":
                for tr in el.select("tr"):
                    tds = tr.select("td")
                    if len(tds) >= 2:
                        raw_name = tds[0].get_text(strip=True)
                        raw_placement = tds[1].get_text(strip=True)
                        if not raw_name or raw_name.lower() in ("name", "student"):
                            continue
                        year = None
                        if len(tds) >= 3:
                            year = parse_year(tds[2].get_text(strip=True))
                        rows.append(PlacementRow(
                            raw_name=raw_name, raw_field=None,
                            raw_placement=raw_placement, raw_position=None,
                            graduation_year=year or current_year,
                            row_index=global_index,
                        ))
                        global_index += 1

            elif el.name in ("ul", "ol") and current_year is not None:
                for li in el.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if not text:
                        continue
                    parts = re.split(r"\s*[–—-]\s*", text, maxsplit=1)
                    raw_name = parts[0].strip()
                    raw_placement = parts[1].strip() if len(parts) > 1 else None
                    if not raw_name:
                        continue
                    rows.append(PlacementRow(
                        raw_name=raw_name, raw_field=None,
                        raw_placement=raw_placement, raw_position=None,
                        graduation_year=current_year, row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from Florida State", len(rows))
        return rows
