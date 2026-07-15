# EconJobMarket

Scrapes economics PhD placement pages from top US universities and loads the data into a 3-layer SQLite pipeline (raw → staging → core). Built for analyzing hiring trends, sector breakdowns, and placement outcomes across programs and years.

The unit of analysis is the **PhD program**, not the university — schools like Penn (Wharton Applied Economics vs. SAS Economics) or Berkeley (Economics vs. ARE) run several PhD-granting programs with separate placement records. Every university has a default `Economics PhD` program; named programs are seeded from `config/programs.csv`. Full schema rationale: [docs/DESIGN-v2-programs-faculty.md](docs/DESIGN-v2-programs-faculty.md).

**Current coverage:** 75 universities (top US economics PhD programs per [US News 2025 rankings](https://www.usnews.com/best-graduate-schools/top-humanities-schools/economics-rankings)).

**Tech stack:** Python 3, SQLite, BeautifulSoup, requests, uv

## Quick Start — Just Query the Data

No setup required — just open the SQLite database:

```bash
sqlite3 data/placements.db
```

```sql
-- Browse recent placements (v_placement joins in university/program names)
SELECT candidate_name, university_name, program_slug, graduation_year,
       placement_institution, placement_sector
FROM v_placement
ORDER BY graduation_year DESC
LIMIT 20;
```

## Developer Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
# Install Python dependencies
uv sync

# Create the database (or bring an existing one to the current schema version)
uv run python -m src init-db
```

Schema changes ship as versioned migrations (`src/migrations/`). When the code
is newer than your database file:

```bash
uv run python -m src migrate    # backs up to data/backups/ first, then migrates
```

### Run the scraper

```bash
uv run python -m src scrape harvard          # Scrape one program (slug)
uv run python -m src scrape all              # Scrape all registered parsers
uv run python -m src scrape harvard --dry-run  # Fetch & parse without writing to DB
```

### Import external data

```bash
uv run python -m src import econphdplacements          # Import from econphdplacements.com
uv run python -m src import econphdplacements --dry-run # Preview without writing
```

### Curate data

```bash
# Register named programs (Wharton, Berkeley ARE, ...) from config/programs.csv
uv run python -m src seed-programs

# Correct a scraped placement; the row is locked so re-scrapes can't undo it
uv run python -m src placement edit 1234 --set placement_sector=academic
uv run python -m src placement edit 1234 --set "placement_position=Assistant Professor"
uv run python -m src placement edit 1234 --unlock   # allow scrape updates again
```

Every correction is recorded in `verification_event` with before/after values.

## Database Schema (v2)

All tables live in `data/placements.db`; the schema version is recorded in
`schema_migration`. Data flows through three layers:

```
Fetch HTML ──► raw_fetch ──► Parse ──► stg_placement ──► Clean ──► placement
                  │                        │                          │
                  ▼                        ▼                          ▼
              Raw Layer              Staging Layer               Core Layer
          (exact responses)       (parsed, uncleaned)     (cleaned, deduplicated)
```

Three invariants keep the layers honest:

1. **Raw values are immutable.** `stg_placement` is append-only history;
   `placement.field_of_study_raw` is the verbatim (whitespace-cleaned) scrape
   value and is never canonicalized in place.
2. **Human corrections outrank scrapes.** `placement edit` sets
   `human_locked = 1`; the scraper's upsert carries
   `WHERE placement.human_locked = 0`, so a re-scrape structurally cannot
   clobber a hand-verified row. Every correction lands in `verification_event`.
3. **Core tables carry no denormalized display names.** Query `v_placement`
   for human-readable output; it joins program and university names in.

### Tables

| Table | Layer | What it holds |
|---|---|---|
| `source_university` | reference | One row per university |
| `program` | reference | PhD programs (1 university : N programs). `slug` is the CLI/parser handle; exactly one `is_default = 1` program per university |
| `source_page` | reference | URLs to scrape per program (`page_type`: `placement` or `directory`) |
| `ingest_run` | raw | One row per scrape/import run (timestamps, git SHA) |
| `raw_fetch` | raw | Full HTTP response for every fetched page |
| `stg_placement` | staging | Parsed, uncleaned rows exactly as extracted (append-only; carries `program_id`) |
| `placement` | core | Cleaned, deduplicated placements keyed to `program_id` |
| `verification_event` | audit | Before/after JSON for every human correction |
| `schema_migration` | meta | Applied migration versions |
| `migration_conflict` | meta | Full JSON of any row a migration dropped (nothing is silently deleted) |

### `placement` (core)

| Column | Type | Notes |
|--------|------|-------|
| `placement_id` | integer | Primary key |
| `stg_placement_id` | integer | FK → stg_placement (NULL for imports) |
| `program_id` | integer | FK → program, NOT NULL |
| `candidate_name` | text | NOT NULL, non-empty |
| `graduation_year` | integer | NULL or 1950–2100 |
| `field_of_study_raw` | text | Verbatim scraped field string |
| `placement_institution` | text | NOT NULL, non-empty |
| `placement_position` | text | |
| `placement_sector` | text | `academic` / `private` / `government` / `other` |
| `is_postdoc` | integer | 0/1 |
| `human_locked` | integer | 1 = hand-corrected; scrape upserts skip this row |
| `created_at`, `updated_at` | text | `updated_at` maintained by trigger |

Deduplication key (unique **expression** index, because SQLite treats NULLs as
pairwise-distinct in plain UNIQUE constraints — the v1 key silently admitted
1,261 duplicate NULL-year rows, archived in `migration_conflict` during the v2
migration):

```sql
CREATE UNIQUE INDEX ux_placement_natkey ON placement
    (program_id, candidate_name, COALESCE(graduation_year, -1), placement_institution);
```

### Views

| View | Purpose |
|---|---|
| `v_placement` | Display: placements with university/program names joined in |
| `v_universities_without_default` | QC: every university must keep exactly one default program |
| `v_cross_program_dupes` | QC: identical placements appearing under two programs of one university (re-attribution double-count guard) |

### Entity-Relationship Diagram

```
source_university 1──N program 1──N source_page 1──N raw_fetch N──1 ingest_run
                            │                            │
                            │ 1                          │ 1
                            │                            │
                            N                            N
                       placement N──1 stg_placement ─────┘
                       (program_id)   (program_id, university_id lineage)
```

## Querying the Data

```bash
sqlite3 data/placements.db
```

### Browse placements (paginated)

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position, placement_sector
FROM v_placement
ORDER BY graduation_year DESC, candidate_name
LIMIT 20 OFFSET 0;
```

### Count by university and year

```sql
SELECT university_name, graduation_year, COUNT(*) AS placements
FROM v_placement
GROUP BY university_name, graduation_year
ORDER BY university_name, graduation_year DESC;
```

### Sector breakdown

```sql
SELECT placement_sector, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM v_placement
GROUP BY placement_sector
ORDER BY n DESC;
```

### Search by candidate name

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position
FROM v_placement
WHERE candidate_name LIKE '%smith%';
```

### Find all postdoc placements

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position
FROM v_placement
WHERE is_postdoc = 1
ORDER BY graduation_year DESC;
```

### Top placement institutions

```sql
SELECT placement_institution, COUNT(*) AS hires
FROM v_placement
WHERE placement_institution IS NOT NULL
GROUP BY placement_institution
ORDER BY hires DESC
LIMIT 15;
```

### Year-over-year academic vs private trends

```sql
SELECT graduation_year,
       SUM(CASE WHEN placement_sector = 'academic' THEN 1 ELSE 0 END) AS academic,
       SUM(CASE WHEN placement_sector = 'private' THEN 1 ELSE 0 END) AS private,
       SUM(CASE WHEN placement_sector = 'government' THEN 1 ELSE 0 END) AS government,
       COUNT(*) AS total
FROM v_placement
WHERE graduation_year IS NOT NULL
GROUP BY graduation_year
ORDER BY graduation_year DESC;
```

## Adding a New University

### 1. Add to config

Add a row to `config/universities.csv`:

```csv
slug,name,domain,state,placement_url,in_external_dataset
mit,Massachusetts Institute of Technology,economics.mit.edu,MA,https://economics.mit.edu/academic-programs/phd-program/job-market,no
```

### 2. Create a parser

Create `src/parsers/<slug>.py`. The parser is auto-discovered — no manual registration needed.

```python
import logging
from bs4 import BeautifulSoup
from src.parsers.base import BasePlacementParser, PlacementRow
from src.utils import parse_year

log = logging.getLogger(__name__)

class MyParser(BasePlacementParser):
    university_slug = "<slug>"   # Must match config slug

    def parse(self, html: str, page_url: str) -> list[PlacementRow]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        # Extract placement data from the page HTML.
        # Return a PlacementRow for each candidate:
        #   PlacementRow(raw_name, raw_field, raw_placement,
        #                raw_position, graduation_year, row_index)
        return rows

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        # Return the next page URL for paginated sites, or None.
        return None
```

### 3. Test and run

```bash
uv run python -m src scrape <slug> --dry-run  # Test parsing without DB writes
uv run python -m src scrape <slug>            # Full scrape with DB insert
```

## Project Structure

```
.
├── pyproject.toml                  # Python project config & dependencies (uv)
├── uv.lock                         # Locked dependency versions
├── config/
│   └── universities.csv            # Top 75 US econ departments (single source of truth)
├── data/
│   ├── placements.db               # SQLite database (the dataset)
│   └── imports/                    # Cached external datasets
└── src/
    ├── __init__.py
    ├── __main__.py                 # CLI entry point (scrape, import, init-db, generate)
    ├── scraper.py                  # 4-phase pipeline orchestrator
    ├── database.py                 # SQLite connection, schema, insert/query helpers
    ├── utils.py                    # HTTP fetch, text cleaning, sector classification
    ├── parsers/
    │   ├── __init__.py             # Auto-discovery parser registry (pkgutil-based)
    │   ├── base.py                 # BasePlacementParser + PlacementRow dataclass
    │   ├── harvard.py              # University-specific parsers...
    │   ├── stanford.py
    │   └── ...
    ├── importers/
    │   ├── __init__.py
    │   ├── econphdplacements.py    # JSONL import from econphdplacements.com
    │   └── gap_report.py           # Coverage analysis
    └── tools/
        ├── generate_seed_sql.py    # Generates seed SQL from universities.csv
        ├── generate_parser.py      # LLM-assisted parser generation
        └── test_parser.py          # Parser validation harness
```
