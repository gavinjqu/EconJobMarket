# EconJobMarket

Scrapes economics PhD placement pages from top US universities and loads the data into a 3-layer PostgreSQL pipeline (raw → staging → core). Built for analyzing hiring trends, sector breakdowns, and placement outcomes across programs and years.

**Current coverage:** 50 universities, 44 with placement data — **13,055 placement records** spanning 1987–2025.

**Tech stack:** Python 3, PostgreSQL 16, BeautifulSoup, requests, uv

> **TODO:** Migrate the pipeline to write directly to SQLite, removing the PostgreSQL/Docker dependency entirely. The dataset (~13K rows) doesn't need a server database.

## Quick Start — Just Query the Data

The easiest way to use this dataset is the **SQLite file** — no Postgres, Docker, or Python setup required:

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

The SQLite file is a portable snapshot of the cleaned placement data, regenerated every time the pipeline runs.

## Developer Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Docker (for PostgreSQL)

### Setup

```bash
# Install Python dependencies
uv sync

# Start PostgreSQL
docker compose up -d

# Initialize the database schema and seed data
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/001_schema.sql
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/010_tables_raw.sql
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/020_tables_staging.sql
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/030_tables_core.sql
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/040_indexes.sql
docker exec -i econjobmarket-db-1 psql -U amm -d amm < sql/ddl/055_seed_top50.sql
```

### Run the scraper

```bash
uv run python -m src scrape harvard          # Scrape Harvard only
uv run python -m src scrape all              # Scrape all 50 universities
uv run python -m src scrape harvard --dry-run  # Fetch & parse without writing to DB
```

Each scrape automatically regenerates `data/placements.db` with the latest data.

### Export SQLite manually

```bash
uv run python -m src export                          # Default: data/placements.db
uv run python -m src export --output path/to/out.db  # Custom path
```

### Import external data

```bash
uv run python -m src import econphdplacements          # Import from econphdplacements.com
uv run python -m src import econphdplacements --dry-run # Preview without writing
```

## Database Schema

All tables live in the `amm` schema. Data flows through three layers:

```
Fetch HTML ──► raw_fetch ──► Parse ──► stg_placement ──► Clean ──► placement
                  │                        │                          │
                  ▼                        ▼                          ▼
              Raw Layer              Staging Layer               Core Layer
          (exact responses)       (parsed, uncleaned)     (cleaned, deduplicated)
```

### Raw Layer

#### `amm.source_university`

Master list of universities.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `university_id` | `bigserial` | NO | Primary key |
| `name` | `text` | NO | Full university name |
| `domain` | `text` | YES | Department website domain |
| `country` | `text` | YES | Country code |
| `state` | `text` | YES | US state abbreviation |
| `created_at` | `timestamptz` | NO | Row creation timestamp |

Example:

| university_id | name | domain | country | state |
|---------------|------|--------|---------|-------|
| 1 | Harvard University | economics.harvard.edu | US | MA |
| 2 | Stanford University | economics.stanford.edu | US | CA |

#### `amm.source_page`

URLs to scrape per university.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `page_id` | `bigserial` | NO | Primary key |
| `university_id` | `bigint` | NO | FK → source_university |
| `page_type` | `text` | NO | Page category (e.g., `placement`) |
| `url` | `text` | NO | Full URL to scrape |
| `is_dynamic` | `boolean` | NO | Whether JS rendering is needed |
| `robots_allowed` | `boolean` | YES | robots.txt compliance flag |
| `created_at` | `timestamptz` | NO | Row creation timestamp |

Example:

| page_id | university_id | page_type | url | is_dynamic |
|---------|---------------|-----------|-----|------------|
| 1 | 1 | placement | https://economics.harvard.edu/placement | false |
| 2 | 2 | placement | https://economics.stanford.edu/graduate/student-placement | false |

#### `amm.ingest_run`

Tracks each scrape or import run.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `run_id` | `bigserial` | NO | Primary key |
| `started_at` | `timestamptz` | NO | When the run started |
| `finished_at` | `timestamptz` | YES | When the run finished |
| `git_sha` | `text` | YES | Git commit SHA at scrape time |
| `notes` | `text` | YES | Run metadata (e.g., `scrape:harvard`) |

Example:

| run_id | started_at | finished_at | git_sha | notes |
|--------|------------|-------------|---------|-------|
| 1 | 2026-02-19 05:10:28 | 2026-02-19 05:10:29 | b9227cc | scrape:harvard |
| 2 | 2026-02-19 05:10:29 | 2026-02-19 05:10:57 | b9227cc | scrape:stanford |

#### `amm.raw_fetch`

Full HTTP response for each fetched page.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `fetch_id` | `bigserial` | NO | Primary key |
| `run_id` | `bigint` | NO | FK → ingest_run |
| `page_id` | `bigint` | NO | FK → source_page |
| `fetched_at` | `timestamptz` | NO | Fetch timestamp |
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

#### `amm.stg_placement`

Parsed but uncleaned placement records. Raw values are preserved exactly as extracted from HTML for debugging parser issues without re-fetching.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `stg_placement_id` | `bigserial` | NO | Primary key |
| `fetch_id` | `bigint` | YES | FK → raw_fetch (NULL for imports) |
| `university_id` | `bigint` | YES | FK → source_university |
| `raw_name` | `text` | YES | Candidate name as scraped |
| `raw_field` | `text` | YES | Field of study as scraped |
| `raw_placement` | `text` | YES | Placement institution as scraped |
| `raw_position` | `text` | YES | Position title as scraped |
| `raw_sector` | `text` | YES | Sector label as scraped |
| `graduation_year` | `integer` | YES | Graduation/placement year |
| `row_index` | `integer` | YES | Position on the source page |
| `parsed_at` | `timestamptz` | YES | When this row was parsed |
| `parse_error` | `text` | YES | Error message if parsing failed |

Example:

| stg_placement_id | fetch_id | university_id | raw_name | raw_placement | graduation_year | row_index |
|------------------|----------|---------------|----------|---------------|-----------------|-----------|
| 1 | 1 | 1 | Constanza Abuin | John Hopkins University | 2025 | 0 |
| 2 | 1 | 1 | Maxim Alekseev | Hong Kong University of Science and Technology | 2025 | 1 |

### Core Layer

#### `amm.placement`

Cleaned, deduplicated, query-ready placement records. Deduplication key: `UNIQUE (university_id, candidate_name, graduation_year, placement_institution)`. Subsequent runs upsert existing records.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `placement_id` | `bigserial` | NO | Primary key |
| `stg_placement_id` | `bigint` | YES | FK → stg_placement |
| `university_id` | `bigint` | YES | FK → source_university |
| `university_name` | `text` | YES | Denormalized university name |
| `candidate_name` | `text` | YES | Cleaned candidate name |
| `graduation_year` | `integer` | YES | Graduation/placement year |
| `field_of_study` | `text` | YES | Normalized field of study |
| `placement_institution` | `text` | YES | Cleaned institution name |
| `placement_position` | `text` | YES | Cleaned position title |
| `placement_sector` | `text` | YES | Classified sector (`academic`, `private`, `government`, `other`) |
| `is_postdoc` | `boolean` | YES | Whether this is a postdoc placement |
| `created_at` | `timestamptz` | YES | Row creation timestamp |
| `updated_at` | `timestamptz` | YES | Last update timestamp |

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

### SQLite (recommended)

```bash
sqlite3 data/placements.db
```

### PostgreSQL

```bash
docker exec -it econjobmarket-db-1 psql -U amm -d amm
```

> Note: SQLite queries below omit the `amm.` schema prefix. For PostgreSQL, prefix table names with `amm.` (e.g., `amm.placement`).

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

### 2. Regenerate seed SQL

```bash
python -m src.tools.generate_seed_sql
```

Then apply the generated `sql/ddl/055_seed_top50.sql` to your database.

### 3. Create a parser

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

### 4. Test and run

```bash
uv run python -m src scrape <slug> --dry-run  # Test parsing without DB writes
uv run python -m src scrape <slug>            # Full scrape with DB insert
```

## Project Structure

```
.
├── docker-compose.yml              # PostgreSQL 16 service
├── pyproject.toml                  # Python project config & dependencies (uv)
├── uv.lock                         # Locked dependency versions
├── .env                            # Database credentials (not committed)
├── config/
│   └── universities.csv            # Top 50 US econ departments (single source of truth)
├── sql/
│   └── ddl/
│       ├── 001_schema.sql          # Create amm schema
│       ├── 010_tables_raw.sql      # ingest_run, source_university, source_page, raw_fetch
│       ├── 020_tables_staging.sql  # stg_placement
│       ├── 030_tables_core.sql     # placement
│       ├── 040_indexes.sql         # All indexes
│       └── 055_seed_top50.sql      # Generated seed data for all 50 universities
├── data/
│   ├── placements.db               # SQLite snapshot (auto-generated)
│   └── imports/                    # Cached external datasets
└── src/
    ├── __init__.py
    ├── __main__.py                 # CLI entry point (scrape, import, export, generate)
    ├── scraper.py                  # 4-phase pipeline orchestrator
    ├── database.py                 # Connection pool, insert/query helpers
    ├── export_sqlite.py            # PostgreSQL → SQLite snapshot export
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
