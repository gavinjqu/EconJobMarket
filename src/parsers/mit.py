"""MIT Economics placement page parser.

NOTE: MIT does not publish structured historical placement data on the web.
Past placements are only available as PDFs. This parser extracts current
job market candidates (names + fields) from the department job market page.
Placement destinations are not available until the PDF is updated post-season.
"""

import logging

from bs4 import BeautifulSoup

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class MITParser(BasePlacementParser):
    university_slug = "mit"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        global_index = 0

        # Candidates are in <figure class="caption caption-img"> elements.
        # Each <figcaption> contains: <a>Name</a><br/>Field1<br/>Field2...
        for fig in soup.select("figure.caption.caption-img"):
            caption = fig.select_one("figcaption")
            if not caption:
                continue

            link = caption.select_one("a")
            if not link:
                continue
            raw_name = link.get_text(strip=True)
            if not raw_name:
                continue

            # Fields are the text nodes after the <a> tag, separated by <br>
            fields = []
            for child in caption.children:
                if child.name == "a":
                    continue
                if child.name == "br":
                    continue
                text = (
                    child.get_text(strip=True) if hasattr(child, "get_text") else str(child).strip()
                )
                if text:
                    fields.append(text)

            raw_field = "; ".join(fields) if fields else None

            rows.append(
                PlacementRow(
                    raw_name=raw_name,
                    raw_field=raw_field,
                    raw_placement=None,
                    raw_position=None,
                    graduation_year=None,
                    row_index=global_index,
                )
            )
            global_index += 1

        log.info("Parsed %d candidates from MIT job market page", len(rows))
        return rows
