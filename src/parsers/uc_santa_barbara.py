"""UC Santa Barbara placement page parser.

UCSB lists placements in a CKEditor accordion (<dl>) grouped by academic year.
Each <dt> contains the year range (e.g. "2025-2026") and each <dd> contains a
<ul> of placements. Each <li> has the institution in <strong> followed by a
dash separator and the position title.

Note: This page does NOT include student names — only institution and position.
raw_name is set to "Unknown" for every entry.
"""

import re
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)

_DASH_RE = re.compile(r"\s*[\u2013\u2014–—-]\s*")


def _extract_year(dt_text: str) -> int | None:
    """Extract the graduation year from a range like '2024-2025'.

    Uses the first (earlier) year as that typically represents when
    the student graduated / entered the job market.
    """
    return parse_year(dt_text)


def _parse_entry(li_tag) -> tuple[str | None, str | None]:
    """Parse a <li> entry into (institution, position).

    Typical formats:
      <strong>Institution</strong> - Position
      <strong>Institution</strong> – Position
      <strong>Institution</strong><span> - Position</span>
      <strong>Alibaba</strong> Group - Economist   (institution spills out of bold)

    Strategy: split full text on the dash separator. The first part is the
    institution, the rest is the position. This handles cases where parts of
    the institution name fall outside the <strong> tag.
    """
    full_text = li_tag.get_text(strip=True)
    if not full_text:
        return None, None

    parts = _DASH_RE.split(full_text, maxsplit=1)
    institution = parts[0].strip() if parts else full_text.strip()
    position = parts[1].strip() if len(parts) > 1 else None

    # Clean up: some institution names end with a closing paren that got
    # split oddly, e.g. "Peking University (HSBC Business School" + ") - ..."
    # Rejoin if the position starts with ")"
    if position and position.startswith(")"):
        position = position.lstrip(")").strip()
        institution = institution + ")"
        # Re-strip dash from position if one remains
        position = _DASH_RE.sub("", position, count=1).strip() or None

    return institution or None, position


class UCSantaBarbaraParser(BasePlacementParser):
    university_slug = "uc_santa_barbara"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[PlacementRow] = []
        global_index = 0

        # The placements are inside a <dl class="ckeditor-accordion">
        accordion = soup.find("dl", class_="ckeditor-accordion")
        if not accordion:
            log.warning("No ckeditor-accordion <dl> found on UCSB placements page")
            return rows

        current_year: int | None = None

        for child in accordion.children:
            if child.name == "dt":
                current_year = _extract_year(child.get_text(strip=True))
            elif child.name == "dd":
                lis = child.find_all("li")
                for li in lis:
                    institution, position = _parse_entry(li)
                    if not institution:
                        continue

                    rows.append(PlacementRow(
                        raw_name="Unknown",
                        raw_field=None,
                        raw_placement=institution,
                        raw_position=position,
                        graduation_year=current_year,
                        row_index=global_index,
                    ))
                    global_index += 1

        log.info("Parsed %d placement rows from UC Santa Barbara", len(rows))
        return rows
