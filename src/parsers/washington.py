"""University of Washington placement page parser.

Washington lists placements organized by year with headings followed by
tables. Tables typically have columns for Name, Placement/Employer,
and optionally Field/Area and Position. Some years may use paragraph
or list-based formats instead of tables.
"""

import logging
import re

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class WashingtonParser(BasePlacementParser):
    university_slug = "washington"

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _header_col_map(header_row):
        """Return a dict mapping normalised purpose -> column index."""
        cells = header_row.find_all(["th", "td"])
        mapping = {}
        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True).lower()
            if "name" in text or "student" in text:
                mapping["name"] = i
            elif "field" in text or "area" in text or "specializ" in text:
                mapping["field"] = i
            elif any(
                kw in text
                for kw in (
                    "placement",
                    "employer",
                    "institution",
                    "organization",
                    "company",
                    "firm",
                )
            ):
                mapping["placement"] = i
            elif "position" in text or "title" in text or "role" in text:
                mapping["position"] = i
            elif "year" in text or "date" in text:
                mapping["year"] = i
        return mapping

    def _parse_table(self, table, current_year, rows, global_index):
        """Parse a single table and append PlacementRow objects to *rows*."""
        trs = table.find_all("tr")
        if not trs:
            return global_index

        # Try to detect a header row
        header = trs[0]
        col_map = self._header_col_map(header)

        # If header looks meaningful, skip it; otherwise treat row 0 as data
        data_start = 1 if col_map else 0

        # Fallback positional mapping when no header keywords found
        if not col_map:
            # Peek at column count from first data row
            sample = trs[0].find_all("td")
            ncols = len(sample)
            if ncols >= 3:
                col_map = {"name": 0, "placement": 1, "field": 2}
            elif ncols == 2:
                col_map = {"name": 0, "placement": 1}

        for tr in trs[data_start:]:
            tds = tr.find_all("td")
            if not tds:
                continue

            def _cell(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(tds):
                    return tds[idx].get_text(strip=True) or None
                return None

            raw_name = _cell("name")
            if not raw_name:
                continue

            year = current_year
            year_cell = _cell("year")
            if year_cell:
                parsed = parse_year(year_cell)
                if parsed:
                    year = parsed

            rows.append(
                PlacementRow(
                    raw_name=raw_name,
                    raw_field=_cell("field"),
                    raw_placement=_cell("placement"),
                    raw_position=_cell("position"),
                    graduation_year=year,
                    row_index=global_index,
                )
            )
            global_index += 1

        return global_index

    def _parse_list_items(self, ul_or_ol, current_year, rows, global_index):
        """Parse ul/ol list entries of the form 'Name – Placement' or
        'Name, Placement'."""
        for li in ul_or_ol.find_all("li", recursive=False):
            text = li.get_text(strip=True)
            if not text:
                continue

            # Try splitting on common separators: em-dash, en-dash, pipe, colon
            parts = re.split(r"\s*[–—|]\s*", text, maxsplit=1)
            if len(parts) == 1:
                # Fall back to comma split
                parts = text.split(",", 1)

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
                    graduation_year=current_year,
                    row_index=global_index,
                )
            )
            global_index += 1

        return global_index

    def _parse_paragraphs(self, container, current_year, rows, global_index):
        """Parse <p> tags that may contain individual placement entries."""
        for p in container.find_all("p", recursive=False):
            text = p.get_text(strip=True)
            if not text or len(text) < 3:
                continue
            # Skip headings-in-paragraphs (all-caps or very short with year)
            if parse_year(text) and len(text) < 20:
                continue

            parts = re.split(r"\s*[–—|]\s*", text, maxsplit=1)
            if len(parts) == 1:
                parts = text.split(",", 1)

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
                    graduation_year=current_year,
                    row_index=global_index,
                )
            )
            global_index += 1

        return global_index

    # ------------------------------------------------------------------ #
    # main parse
    # ------------------------------------------------------------------ #

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[PlacementRow] = []
        global_index = 0
        current_year = None

        # Walk through headings, tables, and lists in document order
        tags_of_interest = soup.find_all(["h2", "h3", "h4", "h5", "table", "ul", "ol"])

        for tag in tags_of_interest:
            # ---- year headings ----
            if tag.name in ("h2", "h3", "h4", "h5"):
                text = tag.get_text(strip=True)
                year = parse_year(text)
                if year:
                    current_year = year
                continue

            # ---- tables ----
            if tag.name == "table":
                global_index = self._parse_table(tag, current_year, rows, global_index)
                continue

            # ---- lists ----
            if tag.name in ("ul", "ol") and current_year:
                global_index = self._parse_list_items(tag, current_year, rows, global_index)
                continue

        # If no structured elements found, try paragraph-based fallback
        if not rows:
            current_year = None
            for el in soup.find_all(["h2", "h3", "h4", "h5", "div"]):
                if el.name in ("h2", "h3", "h4", "h5"):
                    year = parse_year(el.get_text(strip=True))
                    if year:
                        current_year = year
                    continue
                if el.name == "div" and current_year:
                    global_index = self._parse_paragraphs(el, current_year, rows, global_index)

        log.info("Parsed %d placement rows from Washington", len(rows))
        return rows
