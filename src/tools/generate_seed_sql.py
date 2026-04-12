"""Generate seed SQL for all 50 target universities from config/universities.csv.

Usage:
    python -m src.tools.generate_seed_sql
"""

import csv
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_CONFIG = _ROOT / "config" / "universities.csv"
_OUTPUT = _ROOT / "sql" / "ddl" / "055_seed_top50.sql"


def _escape(s: str) -> str:
    """Escape single quotes for SQL string literal."""
    return s.replace("'", "''")


def generate():
    rows = []
    with open(_CONFIG, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    lines = [
        "-- Auto-generated from config/universities.csv",
        "-- Do not edit manually; re-run: python -m src.tools.generate_seed_sql",
        "",
        "-- Seed: source_university (top 50 US econ departments)",
        "INSERT INTO source_university (name, domain, country, state)",
        "VALUES",
    ]

    uni_values = []
    for row in rows:
        name = _escape(row["name"])
        domain = _escape(row["domain"])
        state = _escape(row["state"])
        uni_values.append(f"    ('{name}', '{domain}', 'US', '{state}')")
    lines.append(",\n".join(uni_values))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    # Seed source_page entries for universities with placement_url
    lines.append("-- Seed: source_page (placement URLs)")
    for row in rows:
        url = row.get("placement_url", "").strip()
        if not url:
            continue
        name = _escape(row["name"])
        url_esc = _escape(url)
        lines.append(f"""INSERT INTO source_page (university_id, page_type, url, is_dynamic, robots_allowed)
SELECT u.university_id, 'placement',
       '{url_esc}',
       0, 1
FROM source_university u
WHERE u.name = '{name}'
ON CONFLICT (university_id, page_type, url) DO NOTHING;
""")

    _OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    _OUTPUT.write_text("\n".join(lines))
    print(f"Wrote {_OUTPUT}")


if __name__ == "__main__":
    generate()
