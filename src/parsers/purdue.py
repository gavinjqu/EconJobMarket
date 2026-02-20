"""Purdue University placement page parser.

Purdue's PhD economics page only lists institution names in a
marketing-style bullet list — no individual placement records
with student names or years are available.
This parser returns an empty list — data for Purdue comes from
the external dataset import.
"""

import logging
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class PurdueParser(BasePlacementParser):
    university_slug = "purdue"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Purdue placement page has no individual placement records; "
                 "only marketing summary")
        return []
