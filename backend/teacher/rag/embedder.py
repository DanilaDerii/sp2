"""Embedding worker for teacher-side chunk vectors."""

from dataclasses import dataclass
from typing import Any

import httpx

from backend.teacher.rag.chunker import ChunkedText

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_EMBEDDING_MODEL = "all-minilm:latest"
DEFAULT_HTTP_TIMEOUT = 120.0


@dataclass(slots=True)
class EmbeddedChunk:
    """Chunk data paired with its embedding vector."""

    chunk_id: str
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


def _extract_vectors(payload: dict[str, Any]) -> list[list[float]]:
    """Normalize Ollama embedding responses across compatible formats."""
    if isinstance(payload.get("embeddings"), list):
        return [list(vector) for vector in payload["embeddings"]]

    if isinstance(payload.get("embedding"), list):
        return [list(payload["embedding"])]

    raise RuntimeError("Ollama response did not contain embeddings")


def embed_texts(
    texts: list[str],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
) -> list[list[float]]:
    """Embed a batch of texts with the local Ollama embedding model."""
    if not texts:
        return []

    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        response = client.post(
            "/api/embed",
            json={"model": model, "input": texts},
        )

        if response.status_code == 404:
            legacy_vectors: list[list[float]] = []
            for text in texts:
                legacy_response = client.post(
                    "/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                legacy_response.raise_for_status()
                legacy_payload = legacy_response.json()
                legacy_vectors.extend(_extract_vectors(legacy_payload))
            return legacy_vectors

        response.raise_for_status()
        payload = response.json()
        return _extract_vectors(payload)


def embed_chunks(
    chunks: list[ChunkedText],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
) -> list[EmbeddedChunk]:
    """Embed chunk texts and return chunk records paired with vectors."""
    if not chunks:
        return []

    vectors = embed_texts(
        [chunk.text for chunk in chunks],
        model=model,
        base_url=base_url,
        timeout=timeout,
    )

    if len(vectors) != len(chunks):
        raise RuntimeError(
            "Embedding count mismatch: "
            f"got {len(vectors)} vectors for {len(chunks)} chunks"
        )

    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        embedded_chunks.append(
            EmbeddedChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                source_title=chunk.source_title,
                text=chunk.text,
                vector=vector,
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                section=chunk.section,
                topic=chunk.topic,
                char_count=chunk.char_count,
            )
        )

    return embedded_chunks
