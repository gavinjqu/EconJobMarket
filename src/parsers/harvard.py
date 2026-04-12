import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class HarvardParser(BasePlacementParser):
    university_slug = "harvard"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        for accordion in soup.select("div.hwp-accordion"):
            title_span = accordion.select_one("span.title")
            if not title_span:
                continue
            year = parse_year(title_span.get_text())
            if year is None:
                log.warning("Could not parse year from: %s", title_span.get_text())
                continue

            table = accordion.select_one("table")
            if not table:
                log.warning("No table found for year %d", year)
                continue

            for tr in table.select("tbody tr"):
                tds = tr.select("td")
                if not tds:
                    continue

                # Newer years (2019+) have data-title attrs;
                # older years don't, so fall back to positional.
                name_td = tr.select_one('td[data-title="Name"]')
                if name_td:
                    field_td = tr.select_one('td[data-title="Fields of Study"]')
                    placement_td = tr.select_one('td[data-title="Placement"]')
                elif len(tds) == 3:
                    name_td, field_td, placement_td = tds
                elif len(tds) == 2:
                    name_td, placement_td = tds
                    field_td = None
                else:
                    continue

                raw_name = _cell_text(name_td)
                raw_field = _cell_text(field_td)
                raw_placement = _cell_text(placement_td)

                if not raw_name:
                    continue

                rows.append(
                    PlacementRow(
                        raw_name=raw_name,
                        raw_field=raw_field,
                        raw_placement=raw_placement,
                        raw_position=None,
                        graduation_year=year,
                        row_index=global_index,
                    )
                )
                global_index += 1

        log.info("Parsed %d placement rows from Harvard", len(rows))
        return rows


def _cell_text(td):
    """Extract text from a Harvard table cell."""
    if td is None:
        return None
    content_div = td.select_one("div.hwp-table__cell-content")
    if content_div:
        return content_div.get_text(strip=True) or None
    return td.get_text(strip=True) or None
