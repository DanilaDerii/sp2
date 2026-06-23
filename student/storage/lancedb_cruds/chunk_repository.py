"""CRUD helpers for the student LanceDB pack_chunks table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .connection import get_pack_chunks_table


@dataclass(frozen=True, slots=True)
class PackChunk:
    """One searchable course chunk stored in LanceDB."""

    chunk_id: str
    installed_pack_id: int
    pack_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    vector: list[float]
    chunk_index: int
    page: int | None
    section: str | None
    topic: str | None
    char_count: int


def _installed_pack_filter(installed_pack_id: int) -> str:
    return f"installed_pack_id = {int(installed_pack_id)}"


def _row_to_pack_chunk(row: dict) -> PackChunk:
    return PackChunk(
        chunk_id=row["chunk_id"],
        installed_pack_id=row["installed_pack_id"],
        pack_id=row["pack_id"],
        source_id=row["source_id"],
        source_type=row["source_type"],
        source_title=row["source_title"],
        text=row["text"],
        vector=list(row["vector"]),
        chunk_index=row["chunk_index"],
        page=row["page"],
        section=row["section"],
        topic=row["topic"],
        char_count=row["char_count"],
    )


def _pack_chunk_to_row(chunk: PackChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "installed_pack_id": chunk.installed_pack_id,
        "pack_id": chunk.pack_id,
        "source_id": chunk.source_id,
        "source_type": chunk.source_type,
        "source_title": chunk.source_title,
        "text": chunk.text,
        "vector": chunk.vector,
        "chunk_index": chunk.chunk_index,
        "page": chunk.page,
        "section": chunk.section,
        "topic": chunk.topic,
        "char_count": chunk.char_count,
    }


def add_pack_chunks(chunks: Iterable[PackChunk]) -> int:
    """Append pack chunk rows to LanceDB and return the inserted row count."""
    rows = [_pack_chunk_to_row(chunk) for chunk in chunks]
    if not rows:
        return 0

    table = get_pack_chunks_table()
    table.add(rows)
    return len(rows)


def list_chunks_for_installed_pack(installed_pack_id: int) -> list[PackChunk]:
    """List chunk rows for one local installed pack.

    This is an admin/debug read helper. Retrieval search belongs in a separate
    retrieval module.
    """
    table = get_pack_chunks_table()
    rows = table.to_arrow().to_pylist()
    return [
        _row_to_pack_chunk(row)
        for row in rows
        if row["installed_pack_id"] == installed_pack_id
    ]


def count_chunks_for_installed_pack(installed_pack_id: int) -> int:
    """Count chunk rows for one local installed pack."""
    table = get_pack_chunks_table()
    return table.count_rows(_installed_pack_filter(installed_pack_id))


def delete_chunks_for_installed_pack(installed_pack_id: int) -> int:
    """Delete chunk rows for one local installed pack and return rows deleted."""
    table = get_pack_chunks_table()
    result = table.delete(_installed_pack_filter(installed_pack_id))
    return result.num_deleted_rows
