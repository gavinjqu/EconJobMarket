"""Vanderbilt University placement page parser.

Vanderbilt uses Bootstrap accordion panels. Each panel has an h4 title
like "Class of 2025". Inside each panel-body, entries are <p> blocks
with <strong>Name</strong> followed by position/institution text.

Two sub-formats exist:
  - Format A (recent): separate <p> for name and placement
  - Format B (older): <strong>Name</strong><br/>lines within one <p>
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)


class VanderbiltParser(BasePlacementParser):
    university_slug = "vanderbilt"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        idx = 0

        for panel in soup.find_all("div", class_="panel"):
            title = panel.find(class_="panel-title")
            if not title:
                continue
            year = parse_year(title.get_text())
            if not year:
                continue

            body = panel.find(class_="panel-body")
            if not body:
                continue

            paragraphs = body.find_all("p")
            i = 0
            while i < len(paragraphs):
                p = paragraphs[i]
                strong = p.find("strong")
                if not strong:
                    i += 1
                    continue

                name = strong.get_text(strip=True)
                if not name:
                    i += 1
                    continue

                # Check if this <p> also contains placement info (Format B)
                full_text = p.get_text(separator="\n", strip=True)
                lines = [ln.strip() for ln in full_text.split("\n") if ln.strip()]

                if len(lines) > 1:
                    # Format B: name + placement in same <p>
                    placement_lines = lines[1:]
                    placement = " ".join(placement_lines)
                else:
                    # Format A: next <p> is the placement
                    placement = None
                    if i + 1 < len(paragraphs):
                        next_p = paragraphs[i + 1]
                        if not next_p.find("strong"):
                            placement = next_p.get_text(strip=True)
                            i += 1

                rows.append(
                    PlacementRow(
                        raw_name=name,
                        raw_field=None,
                        raw_placement=placement,
                        raw_position=None,
                        graduation_year=year,
                        row_index=idx,
                    )
                )
                idx += 1
                i += 1

        log.info("Parsed %d placement rows from Vanderbilt", len(rows))
        return rows
