import os
import logging
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME", "amm"),
            user=os.getenv("DB_USER", "amm"),
            password=os.getenv("DB_PASSWORD", ""),
        )
    return _pool


@contextmanager
def get_conn():
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def close_pool():
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None


# --------------- insert helpers ---------------

def insert_ingest_run(conn, git_sha=None, notes=None):
    sql = """
        INSERT INTO amm.ingest_run (git_sha, notes)
        VALUES (%s, %s)
        RETURNING run_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (git_sha, notes))
        return cur.fetchone()[0]


def finish_ingest_run(conn, run_id):
    sql = "UPDATE amm.ingest_run SET finished_at = now() WHERE run_id = %s"
    with conn.cursor() as cur:
        cur.execute(sql, (run_id,))


def insert_raw_fetch(conn, run_id, page_id, status_code, content_type,
                     body_text, body_hash, error=None):
    sql = """
        INSERT INTO amm.raw_fetch
            (run_id, page_id, status_code, content_type, body_text, body_hash, error)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING fetch_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (run_id, page_id, status_code, content_type,
                          body_text, body_hash, error))
        return cur.fetchone()[0]


def insert_stg_placement(conn, fetch_id, university_id, raw_name, raw_field,
                         raw_placement, raw_position, raw_sector,
                         graduation_year, row_index, parse_error=None):
    sql = """
        INSERT INTO amm.stg_placement
            (fetch_id, university_id, raw_name, raw_field, raw_placement,
             raw_position, raw_sector, graduation_year, row_index,
             parsed_at, parse_error)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now(), %s)
        RETURNING stg_placement_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (fetch_id, university_id, raw_name, raw_field,
                          raw_placement, raw_position, raw_sector,
                          graduation_year, row_index, parse_error))
        return cur.fetchone()[0]


def insert_placement(conn, stg_placement_id, university_id, university_name,
                     candidate_name, graduation_year, field_of_study,
                     placement_institution, placement_position,
                     placement_sector, is_postdoc):
    sql = """
        INSERT INTO amm.placement
            (stg_placement_id, university_id, university_name,
             candidate_name, graduation_year, field_of_study,
             placement_institution, placement_position,
             placement_sector, is_postdoc)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (university_id, candidate_name, graduation_year, placement_institution)
        DO UPDATE SET
            field_of_study        = EXCLUDED.field_of_study,
            placement_position    = EXCLUDED.placement_position,
            placement_sector      = EXCLUDED.placement_sector,
            is_postdoc            = EXCLUDED.is_postdoc,
            updated_at            = now()
        RETURNING placement_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (stg_placement_id, university_id, university_name,
                          candidate_name, graduation_year, field_of_study,
                          placement_institution, placement_position,
                          placement_sector, is_postdoc))
        return cur.fetchone()[0]


def get_pages_for_university(conn, university_id):
    sql = """
        SELECT page_id, url, page_type, is_dynamic
        FROM amm.source_page
        WHERE university_id = %s
        ORDER BY page_id
    """
    with conn.cursor() as cur:
        cur.execute(sql, (university_id,))
        return cur.fetchall()


def get_all_universities(conn):
    sql = "SELECT university_id, name FROM amm.source_university ORDER BY university_id"
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def get_university_by_slug(conn, slug):
    """Look up a university by slug matched against the domain column."""
    sql = """
        SELECT university_id, name
        FROM amm.source_university
        WHERE domain ILIKE %s
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (f"%{slug}%",))
        return cur.fetchone()


def get_university_by_name(conn, name):
    """Look up a university by exact name."""
    sql = """
        SELECT university_id, name
        FROM amm.source_university
        WHERE name = %s
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (name,))
        return cur.fetchone()


def get_unprocessed_staging(conn, run_id=None):
    """Get staging rows that haven't been transformed yet.

    Uses LEFT JOIN on raw_fetch so that imported rows (fetch_id IS NULL)
    are included.  The run_id filter only applies when fetch_id is present.
    """
    sql = """
        SELECT s.stg_placement_id, s.fetch_id, s.university_id,
               s.raw_name, s.raw_field, s.raw_placement,
               s.raw_position, s.raw_sector, s.graduation_year,
               u.name AS university_name
        FROM amm.stg_placement s
        LEFT JOIN amm.raw_fetch f ON f.fetch_id = s.fetch_id
        JOIN amm.source_university u ON u.university_id = s.university_id
        WHERE s.parse_error IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM amm.placement pl
              WHERE pl.stg_placement_id = s.stg_placement_id
          )
    """
    params = []
    if run_id is not None:
        sql += " AND (s.fetch_id IS NULL OR f.run_id = %s)"
        params.append(run_id)
    sql += " ORDER BY s.stg_placement_id"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()
