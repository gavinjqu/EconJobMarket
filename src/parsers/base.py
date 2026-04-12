from dataclasses import dataclass


@dataclass
class PlacementRow:
    """One parsed placement row, before any cleaning."""

    raw_name: str
    raw_field: str | None
    raw_placement: str | None
    raw_position: str | None
    graduation_year: int | None
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

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        """Return the next page URL for paginated sites, or None."""
        return None
