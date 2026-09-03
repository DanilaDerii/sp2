"""CRUD helpers for the student installed_packs SQLite table."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from .connection import get_sqlite_connection


@dataclass(frozen=True, slots=True)
class InstalledPack:
    """One locally installed teacher pack."""

    id: int
    pack_id: str
    title: str
    version: str
    description: str | None
    embedding_model: str
    embedding_dim: int
    default_top_k: int
    builder_version: str | None
    pack_created_at: str
    install_path: str
    installed_at: str
    is_active: bool


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_installed_pack(row: sqlite3.Row) -> InstalledPack:
    return InstalledPack(
        id=row["id"],
        pack_id=row["pack_id"],
        title=row["title"],
        version=row["version"],
        description=row["description"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
        default_top_k=row["default_top_k"],
        builder_version=row["builder_version"],
        pack_created_at=row["pack_created_at"],
        install_path=row["install_path"],
        installed_at=row["installed_at"],
        is_active=bool(row["is_active"]),
    )


def _get_connection(connection: sqlite3.Connection | None) -> tuple[sqlite3.Connection, bool]:
    if connection is not None:
        return connection, False
    return get_sqlite_connection(), True


def create_installed_pack(
    *,
    pack_id: str,
    title: str,
    version: str,
    description: str | None,
    embedding_model: str,
    embedding_dim: int,
    default_top_k: int,
    builder_version: str | None,
    pack_created_at: str,
    install_path: str,
    installed_at: str | None = None,
    is_active: bool = True,
    connection: sqlite3.Connection | None = None,
) -> InstalledPack:
    """Create one installed pack row and return it."""
    conn, should_close = _get_connection(connection)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO installed_packs (
                    pack_id,
                    title,
                    version,
                    description,
                    embedding_model,
                    embedding_dim,
                    default_top_k,
                    builder_version,
                    pack_created_at,
                    install_path,
                    installed_at,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pack_id,
                    title,
                    version,
                    description,
                    embedding_model,
                    embedding_dim,
                    default_top_k,
                    builder_version,
                    pack_created_at,
                    install_path,
                    installed_at or _utc_now_iso(),
                    int(is_active),
                ),
            )
            installed_pack_id = int(cursor.lastrowid)

        installed_pack = get_installed_pack(installed_pack_id, connection=conn)
        if installed_pack is None:
            raise RuntimeError(f"Inserted installed_pack was not found: {installed_pack_id}")
        return installed_pack
    finally:
        if should_close:
            conn.close()


def get_installed_pack(
    installed_pack_id: int,
    *,
    connection: sqlite3.Connection | None = None,
) -> InstalledPack | None:
    """Read one installed pack by local primary key."""
    conn, should_close = _get_connection(connection)
    try:
        row = conn.execute(
            """
            SELECT *
            FROM installed_packs
            WHERE id = ?
            """,
            (installed_pack_id,),
        ).fetchone()
        return _row_to_installed_pack(row) if row is not None else None
    finally:
        if should_close:
            conn.close()


def list_installed_packs(
    *,
    pack_id: str | None = None,
    active_only: bool = False,
    connection: sqlite3.Connection | None = None,
) -> list[InstalledPack]:
    """List installed packs, optionally filtered by logical pack id or active status."""
    conn, should_close = _get_connection(connection)
    try:
        conditions: list[str] = []
        values: list[object] = []

        if pack_id is not None:
            conditions.append("pack_id = ?")
            values.append(pack_id)
        if active_only:
            conditions.append("is_active = 1")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        rows = conn.execute(
            f"""
            SELECT *
            FROM installed_packs
            {where_clause}
            ORDER BY installed_at DESC, id DESC
            """,
            values,
        ).fetchall()
        return [_row_to_installed_pack(row) for row in rows]
    finally:
        if should_close:
            conn.close()


def update_installed_pack_active(
    installed_pack_id: int,
    *,
    is_active: bool,
    connection: sqlite3.Connection | None = None,
) -> InstalledPack | None:
    """Update active status for one installed pack and return the updated row."""
    conn, should_close = _get_connection(connection)
    try:
        with conn:
            conn.execute(
                """
                UPDATE installed_packs
                SET is_active = ?
                WHERE id = ?
                """,
                (int(is_active), installed_pack_id),
            )
        return get_installed_pack(installed_pack_id, connection=conn)
    finally:
        if should_close:
            conn.close()


def delete_installed_pack(
    installed_pack_id: int,
    *,
    connection: sqlite3.Connection | None = None,
) -> bool:
    """Delete one installed pack row by local primary key."""
    conn, should_close = _get_connection(connection)
    try:
        with conn:
            cursor = conn.execute(
                """
                DELETE FROM installed_packs
                WHERE id = ?
                """,
                (installed_pack_id,),
            )
        return cursor.rowcount > 0
    finally:
        if should_close:
            conn.close()
