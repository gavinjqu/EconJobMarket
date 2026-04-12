"""Michigan State University placement page parser.

Michigan State uses accordion sections with year labels (a.collapsed)
and collapse divs containing p tags: "Name, Position, Institution".
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class MichiganStateParser(BasePlacementParser):
    university_slug = "michigan_state"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Find accordion links with years
        for link in soup.find_all("a", class_="collapsed"):
            text = link.get_text(strip=True)
            year = parse_year(text)
            if not year:
                continue

            # Find the target collapse div
            target_id = link.get("data-target") or link.get("href", "")
            target_id = target_id.lstrip("#")
            if not target_id:
                continue

            content = soup.find(id=target_id)
            if not content:
                continue

            for p in content.find_all("p"):
                entry = p.get_text(strip=True)
                if not entry:
                    continue

                # Format: "Name, Position, Institution"
                parts = entry.split(",", 1)
                raw_name = parts[0].strip() or None

                if not raw_name:
                    continue

                raw_placement = parts[1].strip().strip(",; ") if len(parts) > 1 else None

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

        log.info("Parsed %d placement rows from Michigan State", len(rows))
        return rows
