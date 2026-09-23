"""CRUD helpers for the student app_settings SQLite table."""

from __future__ import annotations

import sqlite3

from .connection import get_sqlite_connection


def _get_connection(connection: sqlite3.Connection | None) -> tuple[sqlite3.Connection, bool]:
    if connection is not None:
        return connection, False
    return get_sqlite_connection(), True


def get_setting(
    key: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> str | None:
    """Read one setting value by key, or None if it has never been set."""
    conn, should_close = _get_connection(connection)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
        return row["value"] if row is not None else None
    finally:
        if should_close:
            conn.close()


def set_setting(
    key: str,
    value: str,
    *,
    connection: sqlite3.Connection | None = None,
) -> None:
    """Create or replace one setting value by key."""
    conn, should_close = _get_connection(connection)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
    finally:
        if should_close:
            conn.close()
