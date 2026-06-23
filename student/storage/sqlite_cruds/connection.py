"""SQLite connection helpers for student runtime storage."""

import sqlite3
from pathlib import Path


STORAGE_DIR = Path(__file__).resolve().parents[1]
SQLITE_DIR = STORAGE_DIR / "sqlite_storage"
SQLITE_DB_PATH = SQLITE_DIR / "student_app.db"


def get_sqlite_connection(db_path: str | Path = SQLITE_DB_PATH) -> sqlite3.Connection:
    """Open the student SQLite database with project defaults."""
    resolved_path = Path(db_path).expanduser().resolve()
    connection = sqlite3.connect(resolved_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection
