import re
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)

_POSITION_SPLIT = re.compile(
    r"^((?:postdoc|post-doc|assistant professor|associate professor|"
    r"lecturer|visiting|research fellow|economist)[^,]*),\s*(.+)$",
    re.IGNORECASE,
)


class StanfordParser(BasePlacementParser):
    university_slug = "stanford"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for table in soup.select("table.cols-3"):
            time_el = table.select_one("caption time")
            if time_el:
                year = parse_year(time_el.get_text(strip=True))
            else:
                year = None
                log.warning("No <time> element found in table caption")

            for tr in table.select("tbody tr"):
                name_td = tr.select_one("td.views-field-title")
                field_td = tr.select_one(
                    "td.views-field-field-hs-person-interests"
                )
                placement_td = tr.select_one("td.views-field-custm-placement")

                raw_name = _cell_text(name_td)
                raw_field = _cell_text(field_td)
                raw_placement_full = _cell_text(placement_td)

                if not raw_name:
                    continue

                raw_position = None
                raw_placement = raw_placement_full
                if raw_placement_full:
                    m = _POSITION_SPLIT.match(raw_placement_full)
                    if m:
                        raw_position = m.group(1).strip()
                        raw_placement = m.group(2).strip()

                rows.append(PlacementRow(
                    raw_name=raw_name,
                    raw_field=raw_field,
                    raw_placement=raw_placement,
                    raw_position=raw_position,
                    graduation_year=year,
                    row_index=global_index,
                ))
                global_index += 1

        log.info("Parsed %d rows from Stanford (page: %s)",
                 len(rows), page_url)
        return rows

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("li a"):
            if "next" in a.get_text(strip=True).lower():
                href = a.get("href")
                if href:
                    return urljoin(current_url, href)
        return None


def _cell_text(td):
    if td is None:
        return None
    return td.get_text(strip=True) or None
