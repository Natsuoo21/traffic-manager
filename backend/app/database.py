import sqlite3
import uuid
from pathlib import Path

from loguru import logger

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _connect(uri: str) -> sqlite3.Connection:
    """Open a connection by URI or file path."""
    if uri.startswith("file:"):
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(uri)
        conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


class Database:
    """Simple database wrapper for the traffic manager."""

    def __init__(self, db_path: str):
        self.db_path = db_path

        # For in-memory DBs, use a unique named shared cache so each
        # Database instance is isolated but multiple connections share data.
        if db_path == ":memory:":
            name = uuid.uuid4().hex[:8]
            self._uri = f"file:mem_{name}?mode=memory&cache=shared"
        else:
            self._uri = db_path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._keeper = _connect(self._uri)
        schema_sql = _SCHEMA_PATH.read_text()
        self._keeper.executescript(schema_sql)
        self._keeper.commit()
        logger.info(f"Database initialized at {db_path}")

    def connection(self) -> sqlite3.Connection:
        return _connect(self._uri)

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
