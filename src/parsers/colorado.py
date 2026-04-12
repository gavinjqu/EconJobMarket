import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class ColoradoParser(BasePlacementParser):
    university_slug = "colorado"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0
        current_year = None

        for el in soup.find_all(["h3", "ul"]):
            if el.name == "h3":
                year = parse_year(el.get_text(strip=True))
                if year:
                    current_year = year
                continue

            if el.name == "ul" and current_year is not None:
                for li in el.find_all("li"):
                    full_text = li.get_text(separator="\n", strip=True)
                    lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]
                    if not lines:
                        continue
                    # Name is in <b> tag or first line
                    b_tag = li.find("b")
                    raw_name = b_tag.get_text(strip=True) if b_tag else lines[0]
                    if not raw_name:
                        continue
                    raw_placement = None
                    raw_position = None
                    # Placement info is in subsequent lines
                    placement_lines = lines[1:] if not b_tag else lines[1:]
                    if placement_lines:
                        placement_text = placement_lines[0]
                        parts = placement_text.split(",", 1)
                        if len(parts) == 2:
                            raw_position = parts[0].strip()
                            raw_placement = parts[1].strip()
                        else:
                            raw_placement = placement_text

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

        log.info("Parsed %d placement rows from Colorado", len(rows))
        return rows
