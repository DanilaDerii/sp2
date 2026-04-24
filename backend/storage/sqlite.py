"""SQLite bootstrap for SP2 runtime state."""

import sqlite3
from typing import Any

from backend.core.paths import SQLITE_DB_PATH, ensure_runtime_dirs


def get_connection() -> sqlite3.Connection:
    """Open a connection to the local SQLite runtime database."""
    ensure_runtime_dirs()
    connection = sqlite3.connect(SQLITE_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the SQLite runtime database and initial v1 tables."""
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS installed_packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT NOT NULL,
                title TEXT NOT NULL,
                version TEXT NOT NULL,
                install_path TEXT NOT NULL,
                installed_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                pack_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            );
            """
        )


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert a SQLite row to a plain dict for easier prototype use."""
    if row is None:
        return None
    return dict(row)


# InstalledPack CRUD
def create_installed_pack(
    pack_id: str,
    title: str,
    version: str,
    install_path: str,
    installed_at: str,
    is_active: bool = True,
) -> int:
    """Insert an installed pack record and return its new local row id."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO installed_packs (
                pack_id,
                title,
                version,
                install_path,
                installed_at,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pack_id, title, version, install_path, installed_at, int(is_active)),
        )
        return int(cursor.lastrowid)


def list_installed_packs() -> list[dict[str, Any]]:
    """Return all installed packs ordered by newest first."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, pack_id, title, version, install_path, installed_at, is_active
            FROM installed_packs
            ORDER BY installed_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_installed_pack(local_id: int) -> dict[str, Any] | None:
    """Return one installed pack by its local SQLite id."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, pack_id, title, version, install_path, installed_at, is_active
            FROM installed_packs
            WHERE id = ?
            """,
            (local_id,),
        ).fetchone()
    return _row_to_dict(row)


def update_installed_pack_active(local_id: int, is_active: bool) -> None:
    """Update whether an installed pack is active."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE installed_packs
            SET is_active = ?
            WHERE id = ?
            """,
            (int(is_active), local_id),
        )


def delete_installed_pack(local_id: int) -> None:
    """Delete one installed pack row by local SQLite id."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM installed_packs WHERE id = ?",
            (local_id,),
        )


# ChatSession CRUD
def create_chat_session(
    pack_id: str,
    title: str,
    created_at: str,
    updated_at: str,
) -> int:
    """Insert a chat session and return its new local row id."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO chat_sessions (pack_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (pack_id, title, created_at, updated_at),
        )
        return int(cursor.lastrowid)


def list_chat_sessions(pack_id: str) -> list[dict[str, Any]]:
    """Return all chat sessions for a given pack."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, pack_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE pack_id = ?
            ORDER BY updated_at DESC, id DESC
            """,
            (pack_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat_session(session_id: int) -> dict[str, Any] | None:
    """Return one chat session by id."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, pack_id, title, created_at, updated_at
            FROM chat_sessions
            WHERE id = ?
            """,
            (session_id,),
        ).fetchone()
    return _row_to_dict(row)


def update_chat_session_title(session_id: int, title: str, updated_at: str) -> None:
    """Update a chat session title and timestamp."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE chat_sessions
            SET title = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, updated_at, session_id),
        )


def update_chat_session_timestamp(session_id: int, updated_at: str) -> None:
    """Update only the session's latest activity timestamp."""
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE chat_sessions
            SET updated_at = ?
            WHERE id = ?
            """,
            (updated_at, session_id),
        )


def delete_chat_session(session_id: int) -> None:
    """Delete a chat session and all of its messages."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM chat_messages WHERE session_id = ?",
            (session_id,),
        )
        connection.execute(
            "DELETE FROM chat_sessions WHERE id = ?",
            (session_id,),
        )


# ChatMessage CRUD
def create_chat_message(
    session_id: int,
    pack_id: str,
    role: str,
    content: str,
    created_at: str,
) -> int:
    """Insert a chat message and return its new local row id."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO chat_messages (session_id, pack_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, pack_id, role, content, created_at),
        )
        return int(cursor.lastrowid)


def list_chat_messages(session_id: int) -> list[dict[str, Any]]:
    """Return all messages for a chat session in chronological order."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, session_id, pack_id, role, content, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_chat_message(message_id: int) -> dict[str, Any] | None:
    """Return one chat message by id."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, session_id, pack_id, role, content, created_at
            FROM chat_messages
            WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
    return _row_to_dict(row)


def delete_chat_message(message_id: int) -> None:
    """Delete one chat message by id."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM chat_messages WHERE id = ?",
            (message_id,),
        )
