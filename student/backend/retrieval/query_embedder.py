"""Student-side question embedding for retrieval."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from student.storage.sqlite_cruds.pack_repository import InstalledPack

from .embedding_model import (
    DEFAULT_QUERY_EMBEDDING_MODEL,
    EmbeddingModelMismatchError,
    EmbeddingModelSpec,
    embedding_spec_for_pack,
)
from .models import QueryEmbedding


DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_HTTP_TIMEOUT_SECONDS = 120.0


class QueryEmbeddingError(RuntimeError):
    """Raised when a student question cannot be embedded for retrieval."""


class EmbeddingDimensionMismatchError(QueryEmbeddingError):
    """Raised when the query vector dimension does not match the installed pack."""


class OllamaRequestError(QueryEmbeddingError):
    """Raised when the local Ollama embedding API returns an error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _normalized_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise QueryEmbeddingError("Ollama base URL must not be empty")
    return normalized


def _post_json(
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            error_body = ""
        detail = f": {error_body}" if error_body else ""
        raise OllamaRequestError(
            f"Ollama embedding request failed with HTTP {exc.code}{detail}",
            status_code=exc.code,
        ) from exc
    except URLError as exc:
        raise OllamaRequestError(f"Could not reach Ollama embedding API: {exc.reason}") from exc

    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise OllamaRequestError("Ollama embedding response was not valid JSON") from exc

    if not isinstance(decoded, dict):
        raise OllamaRequestError("Ollama embedding response must be a JSON object")
    return decoded


def _vector_from_raw(raw_vector: Any) -> list[float]:
    if not isinstance(raw_vector, list):
        raise OllamaRequestError("Ollama embedding vector must be a JSON array")

    try:
        return [float(value) for value in raw_vector]
    except (TypeError, ValueError) as exc:
        raise OllamaRequestError("Ollama embedding vector contains a non-numeric value") from exc


def _extract_vectors(payload: dict[str, Any]) -> list[list[float]]:
    """Normalize Ollama embedding responses across compatible formats."""
    embeddings = payload.get("embeddings")
    if isinstance(embeddings, list):
        return [_vector_from_raw(vector) for vector in embeddings]

    embedding = payload.get("embedding")
    if isinstance(embedding, list):
        return [_vector_from_raw(embedding)]

    raise OllamaRequestError("Ollama response did not contain embeddings")


def _embed_texts(
    texts: list[str],
    *,
    model: str,
    base_url: str,
    timeout: float,
) -> list[list[float]]:
    if not texts:
        return []

    normalized_base_url = _normalized_base_url(base_url)
    try:
        payload = _post_json(
            f"{normalized_base_url}/api/embed",
            {"model": model, "input": texts},
            timeout=timeout,
        )
        return _extract_vectors(payload)
    except OllamaRequestError as exc:
        if exc.status_code != 404:
            raise

    vectors: list[list[float]] = []
    for text in texts:
        payload = _post_json(
            f"{normalized_base_url}/api/embeddings",
            {"model": model, "prompt": text},
            timeout=timeout,
        )
        vectors.extend(_extract_vectors(payload))

    return vectors


def _validate_question(question: str) -> str:
    normalized_question = " ".join(question.split()).strip()
    if not normalized_question:
        raise QueryEmbeddingError("Question must not be empty")
    return normalized_question


def embed_question(
    question: str,
    *,
    model: str = DEFAULT_QUERY_EMBEDDING_MODEL,
    expected_dim: int | None = None,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> QueryEmbedding:
    """Embed one student question with the fixed v1 retrieval embedding model."""
    normalized_question = _validate_question(question)
    vectors = _embed_texts(
        [normalized_question],
        model=model,
        base_url=base_url,
        timeout=timeout,
    )

    if len(vectors) != 1:
        raise QueryEmbeddingError(
            f"Expected one query embedding vector, got {len(vectors)} vectors"
        )

    vector = vectors[0]
    if expected_dim is not None and len(vector) != expected_dim:
        raise EmbeddingDimensionMismatchError(
            "Query embedding dimension does not match installed pack: "
            f"pack={expected_dim}, query={len(vector)}"
        )

    return QueryEmbedding(
        question=normalized_question,
        model=model,
        vector=vector,
    )


def embed_question_with_spec(
    question: str,
    embedding_spec: EmbeddingModelSpec,
    *,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> QueryEmbedding:
    """Embed one question using an explicit retrieval embedding model spec."""
    return embed_question(
        question,
        model=embedding_spec.model,
        expected_dim=embedding_spec.expected_dim,
        base_url=base_url,
        timeout=timeout,
    )


def embed_question_for_pack(
    question: str,
    installed_pack: InstalledPack,
    *,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> QueryEmbedding:
    """Embed a question with the model policy required by an installed pack."""
    return embed_question_with_spec(
        question,
        embedding_spec_for_pack(installed_pack),
        base_url=base_url,
        timeout=timeout,
    )
