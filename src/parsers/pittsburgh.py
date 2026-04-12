"""University of Pittsburgh placement page parser.

Pittsburgh's placement page only links to a PDF with career outcomes.
No inline placement records are available in the HTML.
This parser returns an empty list — data for Pittsburgh comes from
the external dataset import.
"""

import logging

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class PittsburghParser(BasePlacementParser):
    university_slug = "pittsburgh"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Pittsburgh placement page has PDF link only; no inline data to parse")
        return []
