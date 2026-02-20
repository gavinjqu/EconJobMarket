"""University of Chicago placement page parser.

Chicago's placement page is a landing page with general info
about their placement process. It does not list individual
past placement records. Data for Chicago comes from the
external econphdplacements.com import instead.
"""

import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow

log = logging.getLogger(__name__)


class ChicagoParser(BasePlacementParser):
    university_slug = "chicago"

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        log.info("Chicago placement page is a landing page without individual records")
        return []
