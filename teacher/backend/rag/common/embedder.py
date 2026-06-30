"""Embedding worker for teacher-side chunk vectors."""

from typing import Any

import httpx

from .models import ChunkedText, EmbeddedChunk

DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_HTTP_TIMEOUT = 120.0


class EmbeddingRequestError(RuntimeError):
    """Raised when the local embedding API cannot return vectors."""


def _normalized_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise EmbeddingRequestError("LM Studio base URL must not be empty")
    return normalized


def _extract_vectors(payload: dict[str, Any]) -> list[list[float]]:
    """Extract vectors from an OpenAI-compatible embeddings response."""
    data = payload.get("data")
    if not isinstance(data, list):
        raise EmbeddingRequestError("LM Studio embedding response did not contain data")

    vectors: list[list[float]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise EmbeddingRequestError(f"LM Studio embedding data[{index}] must be an object")

        raw_vector = item.get("embedding")
        if not isinstance(raw_vector, list):
            raise EmbeddingRequestError(
                f"LM Studio embedding data[{index}].embedding must be an array"
            )

        try:
            vectors.append([float(value) for value in raw_vector])
        except (TypeError, ValueError) as exc:
            raise EmbeddingRequestError(
                f"LM Studio embedding data[{index}].embedding contains a non-numeric value"
            ) from exc

    return vectors


def embed_texts(
    texts: list[str],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT,
) -> list[list[float]]:
    """Embed a batch of texts with LM Studio's local embeddings API."""
    if not texts:
        return []

    normalized_base_url = _normalized_base_url(base_url)
    with httpx.Client(base_url=normalized_base_url, timeout=timeout) as client:
        try:
            response = client.post("embeddings", json={"model": model, "input": texts})
        except httpx.RequestError as exc:
            raise EmbeddingRequestError(
                f"Could not reach LM Studio embedding API at {normalized_base_url}: {exc}"
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingRequestError(
                "LM Studio embedding request failed: "
                f"HTTP {response.status_code} from {normalized_base_url}/embeddings: {response.text}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise EmbeddingRequestError(
                "LM Studio embedding response was not valid JSON"
            ) from exc
        return _extract_vectors(payload)


def embed_chunks(
    chunks: list[ChunkedText],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
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
