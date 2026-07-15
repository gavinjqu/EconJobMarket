"""Shared migration primitives."""


class MigrationError(RuntimeError):
    """A migration cannot proceed safely; the database was not modified."""


def table_names(conn) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def column_names(conn, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def scalar(conn, sql: str, params=()) -> int:
    return conn.execute(sql, params).fetchone()[0]
