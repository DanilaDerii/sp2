"""LanceDB vector search for installed student pack chunks."""

from __future__ import annotations

from typing import Any

from student.storage.lancedb_cruds.connection import get_pack_chunks_table

from .models import QueryEmbedding, RetrievedChunk


DEFAULT_TOP_K = 5


class ChunkSearchError(RuntimeError):
    """Raised when chunk vector search cannot be performed."""


def _installed_pack_filter(installed_pack_id: int) -> str:
    return f"installed_pack_id = {int(installed_pack_id)}"


def _validate_installed_pack_id(installed_pack_id: int) -> int:
    if isinstance(installed_pack_id, bool) or int(installed_pack_id) <= 0:
        raise ChunkSearchError("installed_pack_id must be a positive integer")
    return int(installed_pack_id)


def _validate_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or int(top_k) <= 0:
        raise ChunkSearchError("top_k must be a positive integer")
    return int(top_k)


def _validate_query_vector(query_vector: list[float]) -> list[float]:
    if not query_vector:
        raise ChunkSearchError("query_vector must not be empty")

    try:
        return [float(value) for value in query_vector]
    except (TypeError, ValueError) as exc:
        raise ChunkSearchError("query_vector contains a non-numeric value") from exc


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _distance_to_score(distance: float | None) -> float | None:
    if distance is None:
        return None
    if distance < 0:
        return None
    return 1.0 / (1.0 + distance)


def _row_to_retrieved_chunk(row: dict[str, Any]) -> RetrievedChunk:
    distance = _optional_float(row.get("_distance"))
    return RetrievedChunk(
        chunk_id=row["chunk_id"],
        installed_pack_id=int(row["installed_pack_id"]),
        pack_id=row["pack_id"],
        source_id=row["source_id"],
        source_type=row["source_type"],
        source_title=row["source_title"],
        text=row["text"],
        chunk_index=int(row["chunk_index"]),
        page=row["page"],
        section=row["section"],
        topic=row["topic"],
        char_count=int(row["char_count"]),
        distance=distance,
        score=_distance_to_score(distance),
    )


def _within_max_distance(chunk: RetrievedChunk, max_distance: float | None) -> bool:
    if max_distance is None:
        return True
    if chunk.distance is None:
        return False
    return chunk.distance <= max_distance


def search_chunks_by_vector(
    *,
    installed_pack_id: int,
    query_vector: list[float],
    top_k: int = DEFAULT_TOP_K,
    max_distance: float | None = None,
) -> list[RetrievedChunk]:
    """Return nearest chunks for one installed pack and query vector."""
    resolved_installed_pack_id = _validate_installed_pack_id(installed_pack_id)
    resolved_top_k = _validate_top_k(top_k)
    resolved_query_vector = _validate_query_vector(query_vector)

    if max_distance is not None and max_distance < 0:
        raise ChunkSearchError("max_distance must be greater than or equal to 0")

    table = get_pack_chunks_table()
    rows = (
        table.search(resolved_query_vector)
        .where(_installed_pack_filter(resolved_installed_pack_id), prefilter=True)
        .limit(resolved_top_k)
        .to_list()
    )

    chunks = [_row_to_retrieved_chunk(row) for row in rows]
    return [
        chunk for chunk in chunks if _within_max_distance(chunk, max_distance)
    ]


def search_chunks_for_query(
    *,
    installed_pack_id: int,
    query_embedding: QueryEmbedding,
    top_k: int = DEFAULT_TOP_K,
    max_distance: float | None = None,
) -> list[RetrievedChunk]:
    """Return nearest chunks for one installed pack and embedded question."""
    return search_chunks_by_vector(
        installed_pack_id=installed_pack_id,
        query_vector=query_embedding.vector,
        top_k=top_k,
        max_distance=max_distance,
    )
