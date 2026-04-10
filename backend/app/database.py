import sqlite3
from pathlib import Path

from loguru import logger

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a SQLite connection with WAL mode and foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    """Initialize the database: create directory, run schema."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = _SCHEMA_PATH.read_text()
    conn = get_connection(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
    finally:
        conn.close()


class Database:
    """Simple database wrapper for the traffic manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        init_db(db_path)

    def connection(self) -> sqlite3.Connection:
        return get_connection(self.db_path)

    def execute(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        conn = self.connection()
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
            conn.commit()
            return rows
        finally:
            conn.close()

    def execute_many(self, sql: str, params_list: list[tuple]) -> int:
        conn = self.connection()
        try:
            cursor = conn.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def insert(self, sql: str, params: tuple = ()) -> int:
        conn = self.connection()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()
