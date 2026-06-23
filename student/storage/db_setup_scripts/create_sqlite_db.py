"""Create the student SQLite database."""

import sqlite3
from pathlib import Path


STORAGE_DIR = Path(__file__).resolve().parent.parent
SQLITE_DIR = STORAGE_DIR / "sqlite_storage"
SQLITE_DB_PATH = SQLITE_DIR / "student_app.db"


def create_sqlite_db() -> None:
    SQLITE_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(SQLITE_DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    with connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS installed_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT NOT NULL,
                title TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                embedding_model TEXT NOT NULL,
                embedding_dim INTEGER NOT NULL,
                default_top_k INTEGER NOT NULL,
                builder_version TEXT,
                pack_created_at TEXT NOT NULL,
                install_path TEXT NOT NULL UNIQUE,
                installed_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            );

            """
        )

    connection.close()
    print(f"SQLite database created at: {SQLITE_DB_PATH}")


if __name__ == "__main__":
    create_sqlite_db()
