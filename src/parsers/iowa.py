"""University of Iowa placement page parser.

Iowa's PhD economics page only lists a handful of example
institution names in a marketing blurb — no individual placement
records with student names or years are available.
This parser returns an empty list — data for Iowa comes from
the external dataset import.
"""

import logging
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class IowaParser(BasePlacementParser):
    university_slug = "iowa"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Iowa placement page has no individual placement records; "
                 "only marketing summary")
        return []
