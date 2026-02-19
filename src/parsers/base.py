from dataclasses import dataclass
from typing import Optional


@dataclass
class PlacementRow:
    """One parsed placement row, before any cleaning."""
    raw_name: str
    raw_field: Optional[str]
    raw_placement: Optional[str]
    raw_position: Optional[str]
    graduation_year: Optional[int]
    row_index: int


class BasePlacementParser:
    """
    Base class for university placement parsers.

    Subclasses must implement:
        parse(html, page_url) -> list[PlacementRow]
    """

    university_slug: str = ""

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        raise NotImplementedError

    def get_next_page_url(self, html: str, current_url: str) -> Optional[str]:
        """Return the next page URL for paginated sites, or None."""
        return None
