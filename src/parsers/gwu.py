import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class GWUParser(BasePlacementParser):
    university_slug = "gwu"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Structure: <dl> with <dt>YEAR</dt><dd>...entries...</dd>
        # Entries: <p><strong>Name (Advisor)</strong></p> <ul><li>Org; Title</li></ul>
        for dt in soup.find_all("dt"):
            year = parse_year(dt.get_text(strip=True))
            if not year:
                continue

            dd = dt.find_next_sibling("dd")
            if not dd:
                continue

            for strong in dd.find_all("strong"):
                text = strong.get_text(strip=True)
                if not text:
                    continue
                raw_name = re.sub(r"\s*\(.*?\)\s*$", "", text).strip()
                if not raw_name or len(raw_name) < 3:
                    continue

                # Find the next <ul> after this <strong>'s parent <p>
                raw_placement = None
                raw_position = None
                parent_p = strong.parent
                if parent_p:
                    next_ul = parent_p.find_next_sibling("ul")
                    if next_ul:
                        li = next_ul.find("li")
                        if li:
                            placement_text = li.get_text(strip=True)
                            if ";" in placement_text:
                                parts = placement_text.split(";", 1)
                                raw_placement = parts[0].strip()
                                raw_position = parts[1].strip()
                            else:
                                raw_placement = placement_text

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

        log.info("Parsed %d placement rows from GWU", len(rows))
        return rows
