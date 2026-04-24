"""Student-side retrieval over the local LanceDB chunk index."""

from dataclasses import dataclass

from backend.storage.lancedb import search_chunks
from backend.teacher.rag.embedder import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_OLLAMA_BASE_URL,
    embed_texts,
)

DEFAULT_RETRIEVAL_TOP_K = 5


@dataclass(slots=True)
class RetrievedChunk:
    """One retrieved chunk returned for a student question."""

    chunk_id: str
    pack_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: str | None
    section: str | None
    topic: str | None
    distance: float | None


@dataclass(slots=True)
class RetrievalResult:
    """Question embedding plus the retrieved chunks."""

    question: str
    pack_id: str
    query_vector: list[float]
    chunks: list[RetrievedChunk]


def retrieve_chunks_for_question(
    question: str,
    pack_id: str,
    *,
    top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> RetrievalResult:
    """Embed a student question and retrieve the nearest chunks for one pack."""
    normalized_question = question.strip()
    if not normalized_question:
        raise ValueError("Question must not be empty")

    vectors = embed_texts(
        [normalized_question],
        model=embedding_model,
        base_url=ollama_base_url,
    )
    if not vectors:
        raise RuntimeError("Question embedding returned no vector")

    query_vector = vectors[0]
    rows = search_chunks(query_vector, pack_id, limit=top_k)
    chunks = [
        RetrievedChunk(
            chunk_id=row["chunk_id"],
            pack_id=row["pack_id"],
            source_id=row["source_id"],
            source_type=row["source_type"],
            source_title=row["source_title"],
            text=row["text"],
            chunk_index=row["chunk_index"],
            page=row.get("page"),
            section=row.get("section"),
            topic=row.get("topic"),
            distance=row.get("_distance"),
        )
        for row in rows
    ]

    return RetrievalResult(
        question=normalized_question,
        pack_id=pack_id,
        query_vector=query_vector,
        chunks=chunks,
    )
