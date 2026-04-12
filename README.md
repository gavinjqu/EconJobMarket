# EconJobMarket

Scrapes economics PhD placement pages from top US universities and loads the data into a 3-layer SQLite pipeline (raw → staging → core). Built for analyzing hiring trends, sector breakdowns, and placement outcomes across programs and years.

**Current coverage:** 50 universities, 44 with placement data — **13,055 placement records** spanning 1987–2025.

**Tech stack:** Python 3, SQLite, BeautifulSoup, requests, uv

## Quick Start — Just Query the Data

No setup required — just open the SQLite database:

```bash
sqlite3 data/placements.db
```

```sql
-- Browse recent placements
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_sector
FROM placement
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

# Initialize the database (creates data/placements.db with schema + seed data)
uv run python -m src init-db
```

### Run the scraper

```bash
uv run python -m src scrape harvard          # Scrape Harvard only
uv run python -m src scrape all              # Scrape all 50 universities
uv run python -m src scrape harvard --dry-run  # Fetch & parse without writing to DB
```

### Import external data

```bash
uv run python -m src import econphdplacements          # Import from econphdplacements.com
uv run python -m src import econphdplacements --dry-run # Preview without writing
```

## Database Schema

All tables live in `data/placements.db`. Data flows through three layers:

```
Fetch HTML ──► raw_fetch ──► Parse ──► stg_placement ──► Clean ──► placement
                  │                        │                          │
                  ▼                        ▼                          ▼
              Raw Layer              Staging Layer               Core Layer
          (exact responses)       (parsed, uncleaned)     (cleaned, deduplicated)
```

### Raw Layer

#### `source_university`

Master list of universities.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `university_id` | `integer` | NO | Primary key |
| `name` | `text` | NO | Full university name |
| `domain` | `text` | YES | Department website domain |
| `country` | `text` | YES | Country code |
| `state` | `text` | YES | US state abbreviation |
| `created_at` | `text` | NO | Row creation timestamp |

Example:

| university_id | name | domain | country | state |
|---------------|------|--------|---------|-------|
| 1 | Harvard University | economics.harvard.edu | US | MA |
| 2 | Stanford University | economics.stanford.edu | US | CA |

#### `source_page`

URLs to scrape per university.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `page_id` | `integer` | NO | Primary key |
| `university_id` | `integer` | NO | FK → source_university |
| `page_type` | `text` | NO | Page category (e.g., `placement`) |
| `url` | `text` | NO | Full URL to scrape |
| `is_dynamic` | `integer` | NO | Whether JS rendering is needed |
| `robots_allowed` | `integer` | YES | robots.txt compliance flag |
| `created_at` | `text` | NO | Row creation timestamp |

Example:

| page_id | university_id | page_type | url | is_dynamic |
|---------|---------------|-----------|-----|------------|
| 1 | 1 | placement | https://economics.harvard.edu/placement | false |
| 2 | 2 | placement | https://economics.stanford.edu/graduate/student-placement | false |

#### `ingest_run`

Tracks each scrape or import run.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `run_id` | `integer` | NO | Primary key |
| `started_at` | `text` | NO | When the run started |
| `finished_at` | `text` | YES | When the run finished |
| `git_sha` | `text` | YES | Git commit SHA at scrape time |
| `notes` | `text` | YES | Run metadata (e.g., `scrape:harvard`) |

Example:

| run_id | started_at | finished_at | git_sha | notes |
|--------|------------|-------------|---------|-------|
| 1 | 2026-02-19 05:10:28 | 2026-02-19 05:10:29 | b9227cc | scrape:harvard |
| 2 | 2026-02-19 05:10:29 | 2026-02-19 05:10:57 | b9227cc | scrape:stanford |

#### `raw_fetch`

Full HTTP response for each fetched page.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `fetch_id` | `integer` | NO | Primary key |
| `run_id` | `integer` | NO | FK → ingest_run |
| `page_id` | `integer` | NO | FK → source_page |
| `fetched_at` | `text` | NO | Fetch timestamp |
| `status_code` | `integer` | YES | HTTP status code |
| `content_type` | `text` | YES | Response Content-Type header |
| `body_text` | `text` | YES | Full HTML response body |
| `body_hash` | `text` | YES | SHA-256 hash of body_text |
| `error` | `text` | YES | Error message if fetch failed |

Example:

| fetch_id | run_id | page_id | status_code | content_type | body_hash | error |
|----------|--------|---------|-------------|--------------|-----------|-------|
| 1 | 1 | 1 | 200 | text/html; charset=UTF-8 | 4075fa67... | NULL |
| 2 | 2 | 2 | 200 | text/html; charset=UTF-8 | b9948c2d... | NULL |

### Staging Layer

#### `stg_placement`

Parsed but uncleaned placement records. Raw values are preserved exactly as extracted from HTML for debugging parser issues without re-fetching.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `stg_placement_id` | `integer` | NO | Primary key |
| `fetch_id` | `integer` | YES | FK → raw_fetch (NULL for imports) |
| `university_id` | `integer` | YES | FK → source_university |
| `raw_name` | `text` | YES | Candidate name as scraped |
| `raw_field` | `text` | YES | Field of study as scraped |
| `raw_placement` | `text` | YES | Placement institution as scraped |
| `raw_position` | `text` | YES | Position title as scraped |
| `raw_sector` | `text` | YES | Sector label as scraped |
| `graduation_year` | `integer` | YES | Graduation/placement year |
| `row_index` | `integer` | YES | Position on the source page |
| `parsed_at` | `text` | YES | When this row was parsed |
| `parse_error` | `text` | YES | Error message if parsing failed |

Example:

| stg_placement_id | fetch_id | university_id | raw_name | raw_placement | graduation_year | row_index |
|------------------|----------|---------------|----------|---------------|-----------------|-----------|
| 1 | 1 | 1 | Constanza Abuin | John Hopkins University | 2025 | 0 |
| 2 | 1 | 1 | Maxim Alekseev | Hong Kong University of Science and Technology | 2025 | 1 |

### Core Layer

#### `placement`

Cleaned, deduplicated, query-ready placement records. Deduplication key: `UNIQUE (university_id, candidate_name, graduation_year, placement_institution)`. Subsequent runs upsert existing records.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `placement_id` | `integer` | NO | Primary key |
| `stg_placement_id` | `integer` | YES | FK → stg_placement |
| `university_id` | `integer` | YES | FK → source_university |
| `university_name` | `text` | YES | Denormalized university name |
| `candidate_name` | `text` | YES | Cleaned candidate name |
| `graduation_year` | `integer` | YES | Graduation/placement year |
| `field_of_study` | `text` | YES | Normalized field of study |
| `placement_institution` | `text` | YES | Cleaned institution name |
| `placement_position` | `text` | YES | Cleaned position title |
| `placement_sector` | `text` | YES | Classified sector (`academic`, `private`, `government`, `other`) |
| `is_postdoc` | `integer` | YES | Whether this is a postdoc placement |
| `created_at` | `text` | YES | Row creation timestamp |
| `updated_at` | `text` | YES | Last update timestamp |

Example:

| placement_id | university_name | candidate_name | graduation_year | placement_institution | placement_sector | is_postdoc |
|--------------|-----------------|----------------|-----------------|----------------------|-----------------|------------|
| 8 | Harvard University | Leonardo D'Amico | 2025 | University of Chicago Booth School of Business | academic | false |
| 13 | Harvard University | Martin Koenen | 2025 | IIES Stockholm | other | false |

### Entity-Relationship Diagram

```
source_university ─────┐
  PK university_id     │
  name                 │
  domain               │1
  country              ├──────────── source_page
  state                │               PK page_id
                       │               FK university_id
                       │               page_type
                       │               url
                       │               is_dynamic
                       │
                       │            ingest_run
                       │              PK run_id
                       │              started_at
                       │              finished_at
                       │              git_sha
                       │
                       │1           raw_fetch
                       ├──┐          PK fetch_id
                       │  │          FK run_id ──────► ingest_run
                       │  │          FK page_id ─────► source_page
                       │  │          status_code
                       │  │          body_text
                       │  │          body_hash
                       │  │
                       │  │1       stg_placement
                       │  └───────── PK stg_placement_id
                       │             FK fetch_id ────► raw_fetch
                       │  ┌───────── FK university_id
                       │  │          raw_name
                       │  │          raw_field
                       │  │          raw_placement
                       │  │          graduation_year
                       │  │
                       │  │1       placement
                       │  └───────── PK placement_id
                       │             FK stg_placement_id ► stg_placement
                       └──────────── FK university_id
                                     candidate_name
                                     graduation_year
                                     placement_institution
                                     placement_sector
                                     is_postdoc
```

## Querying the Data

```bash
sqlite3 data/placements.db
```

### Browse placements (paginated)

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position, placement_sector
FROM placement
ORDER BY graduation_year DESC, candidate_name
LIMIT 20 OFFSET 0;
```

### Count by university and year

```sql
SELECT university_name, graduation_year, COUNT(*) AS placements
FROM placement
GROUP BY university_name, graduation_year
ORDER BY university_name, graduation_year DESC;
```

### Sector breakdown

```sql
SELECT placement_sector, COUNT(*) AS n,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM placement
GROUP BY placement_sector
ORDER BY n DESC;
```

### Search by candidate name

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position
FROM placement
WHERE candidate_name LIKE '%smith%';
```

### Find all postdoc placements

```sql
SELECT candidate_name, university_name, graduation_year,
       placement_institution, placement_position
FROM placement
WHERE is_postdoc = 1
ORDER BY graduation_year DESC;
```

### Top placement institutions

```sql
SELECT placement_institution, COUNT(*) AS hires
FROM placement
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
FROM placement
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
│   └── universities.csv            # Top 50 US econ departments (single source of truth)
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
    │   ├── harvard.py              # 50 university-specific parsers...
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
