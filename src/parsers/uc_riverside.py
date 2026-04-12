import re
import logging
from bs4 import BeautifulSoup, NavigableString
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class UCRiversideParser(BasePlacementParser):
    university_slug = "uc_riverside"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        # Years are h3 headings, records are paragraphs with name + placement
        content = soup.find("div", class_="entry-content") or soup
        for el in content.find_all(["h3", "p"]):
            if el.name == "h3":
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "p" and current_year is not None:
                text = el.get_text(strip=True)
                if not text or len(text) < 3:
                    continue
                # Skip year-only paragraphs
                if re.match(r"^\d{4}$", text):
                    continue
                # Try to extract name from the text
                # Format: "Name\nPosition, Institution" or just "Name"
                lines = el.get_text(separator="\n", strip=True).split("\n")
                lines = [l.strip() for l in lines if l.strip()]
                if not lines:
                    continue
                raw_name = lines[0]
                raw_placement = None
                raw_position = None
                if len(lines) > 1:
                    placement_text = lines[1]
                    parts = placement_text.split(",", 1)
                    if len(parts) == 2:
                        raw_position = parts[0].strip()
                        raw_placement = parts[1].strip()
                    else:
                        raw_placement = placement_text

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=current_year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d placement rows from UC Riverside", len(rows))
        return rows
