"""University of Wisconsin-Madison placement page parser.

Wisconsin's placement page only contains links to PDF files
for each year's placement data, with no inline placement records.
This parser returns an empty list — data for Wisconsin comes from
the external dataset import.
"""

import logging
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class WisconsinParser(BasePlacementParser):
    university_slug = "wisconsin"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Wisconsin placement page has PDF links only; "
                 "no inline data to parse")
        return []
