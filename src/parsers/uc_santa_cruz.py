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

        # Years as bold headings, records as bullet list items
        # Format: **Name** – Position, Institution
        for el in soup.find_all(["h2", "h3", "h4", "ul"]):
            if el.name in ("h2", "h3", "h4"):
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "ul" and current_year is not None:
                for li in el.find_all("li", recursive=False):
                    text = li.get_text(strip=True)
                    if not text:
                        continue
                    # Try to extract name from bold tag
                    bold = li.find(["strong", "b"])
                    if bold:
                        raw_name = bold.get_text(strip=True)
                        # Get rest of text after the name
                        remainder = text[len(raw_name) :].strip()
                        remainder = re.sub(r"^[\s\-–—]+", "", remainder).strip()
                    else:
                        # Split on dash
                        parts = re.split(r"\s*[–—-]\s*", text, maxsplit=1)
                        raw_name = parts[0].strip()
                        remainder = parts[1].strip() if len(parts) > 1 else ""

                    if not raw_name:
                        continue

                    raw_placement = None
                    raw_position = None
                    if remainder:
                        # Try "Position, Institution"
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
