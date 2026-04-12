import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCSantaCruzParser(BasePlacementParser):
    university_slug = "uc_santa_cruz"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        # Years are <strong> tags containing just a year (e.g., "2026").
        # Entries are <li> with <strong>Name</strong> – Position, Institution.
        for el in soup.find_all(["strong", "li"]):
            if el.name == "strong":
                text = el.get_text(strip=True)
                # Year-only strong tags (not inside a <li>)
                if el.parent and el.parent.name != "li":
                    year = parse_year(text)
                    if year and len(text) <= 10:
                        current_year = year
                continue

            if el.name == "li" and current_year is not None:
                text = el.get_text(strip=True)
                if not text:
                    continue

                bold = el.find("strong")
                if bold:
                    raw_name = bold.get_text(strip=True)
                    remainder = text[len(raw_name) :].strip()
                    remainder = re.sub(r"^[\s\-–—]+", "", remainder).strip()
                else:
                    parts = re.split(r"\s*[–—-]\s*", text, maxsplit=1)
                    raw_name = parts[0].strip()
                    remainder = parts[1].strip() if len(parts) > 1 else ""

                if not raw_name:
                    continue

                raw_placement = None
                raw_position = None
                if remainder:
                    comma_parts = remainder.split(",", 1)
                    if len(comma_parts) == 2:
                        raw_position = comma_parts[0].strip()
                        raw_placement = comma_parts[1].strip()
                    else:
                        raw_placement = remainder

                rows.append(
                    PlacementRow(
                        raw_name=raw_name,
                        raw_field=None,
                        raw_placement=raw_placement,
                        raw_position=raw_position,
                        graduation_year=current_year,
                        row_index=global_index,
                    )
                )
                global_index += 1

        log.info("Parsed %d placement rows from UC Santa Cruz", len(rows))
        return rows
