"""Rutgers University placement page parser.

Rutgers' placement page only links to a PDF with graduate placements.
No inline placement records are available in the HTML.
This parser returns an empty list — data for Rutgers comes from
the external dataset import.
"""

import logging

from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class RutgersParser(BasePlacementParser):
    university_slug = "rutgers"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Rutgers placement page has PDF link only; no inline data to parse")
        return []
