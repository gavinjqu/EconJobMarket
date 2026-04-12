import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class BrandeisParser(BasePlacementParser):
    university_slug = "brandeis"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Structure: <p><strong>Name 'YY</strong><br/>Position<br/>PhD info</p>
        # Year embedded in name as 'YY (two-digit year)
        for p in soup.find_all("p"):
            strong = p.find("strong")
            if not strong:
                continue

            strong_text = strong.get_text(strip=True)
            # Extract year from 'YY pattern
            year_match = re.search(r"['\u2018\u2019](\d{2})", strong_text)
            if not year_match:
                continue

            year_suffix = int(year_match.group(1))
            graduation_year = 1900 + year_suffix if year_suffix > 50 else 2000 + year_suffix

            # Extract name (everything before the 'YY)
            raw_name = strong_text[: year_match.start()].strip()
            if not raw_name:
                continue

            # Get placement from the lines after the name
            lines = p.get_text(separator="\n", strip=True).split("\n")
            lines = [ln.strip() for ln in lines if ln.strip()]

            raw_placement = None
            raw_position = None
            # Skip first line (name), take second line as position/placement
            if len(lines) > 1:
                placement_text = lines[1]
                # Skip "PhD in..." lines
                if not placement_text.lower().startswith("phd"):
                    raw_placement = placement_text

            # If first non-name line was PhD info, try the next
            if not raw_placement and len(lines) > 2:
                for line in lines[1:]:
                    if not line.lower().startswith("phd"):
                        raw_placement = line
                        break

            rows.append(
                PlacementRow(
                    raw_name=raw_name,
                    raw_field=None,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=graduation_year,
                    row_index=global_index,
                )
            )
            global_index += 1

        log.info("Parsed %d placement rows from Brandeis", len(rows))
        return rows
