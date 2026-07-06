"""SQLite connection helpers for student runtime storage."""

import sqlite3
from pathlib import Path

from student.storage.database.setup.create_sqlite_db import SQLITE_DB_PATH


def get_sqlite_connection(db_path: str | Path = SQLITE_DB_PATH) -> sqlite3.Connection:
    """Open the student SQLite database with project defaults."""
    resolved_path = Path(db_path).expanduser().resolve()
    connection = sqlite3.connect(resolved_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection
