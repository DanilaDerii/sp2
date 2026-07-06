"""Student-side question embedding for retrieval."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from storage.cruds.sqlite.pack_repository import InstalledPack

from .embedding_model import (
    DEFAULT_QUERY_EMBEDDING_MODEL,
    EmbeddingModelSpec,
    embedding_spec_for_pack,
)
from .models import QueryEmbedding


DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_HTTP_TIMEOUT_SECONDS = 120.0


class QueryEmbeddingError(RuntimeError):
    """Raised when a student question cannot be embedded for retrieval."""


class EmbeddingDimensionMismatchError(QueryEmbeddingError):
    """Raised when the query vector dimension does not match the installed pack."""


class LMStudioEmbeddingRequestError(QueryEmbeddingError):
    """Raised when the local LM Studio embedding API returns an error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _normalized_base_url(base_url: str) -> str:
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        raise QueryEmbeddingError("LM Studio base URL must not be empty")
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
        raise LMStudioEmbeddingRequestError(
            f"LM Studio embedding request failed with HTTP {exc.code}{detail}",
            status_code=exc.code,
        ) from exc
    except URLError as exc:
        raise LMStudioEmbeddingRequestError(
            f"Could not reach LM Studio embedding API: {exc.reason}"
        ) from exc

    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise LMStudioEmbeddingRequestError(
            "LM Studio embedding response was not valid JSON"
        ) from exc

    if not isinstance(decoded, dict):
        raise LMStudioEmbeddingRequestError(
            "LM Studio embedding response must be a JSON object"
        )
    return decoded


def _vector_from_raw(raw_vector: Any) -> list[float]:
    if not isinstance(raw_vector, list):
        raise LMStudioEmbeddingRequestError(
            "LM Studio embedding vector must be a JSON array"
        )

    try:
        return [float(value) for value in raw_vector]
    except (TypeError, ValueError) as exc:
        raise LMStudioEmbeddingRequestError(
            "LM Studio embedding vector contains a non-numeric value"
        ) from exc


def _extract_vectors(payload: dict[str, Any]) -> list[list[float]]:
    """Extract vectors from an OpenAI-compatible embeddings response."""
    data = payload.get("data")
    if not isinstance(data, list):
        raise LMStudioEmbeddingRequestError(
            "LM Studio embedding response did not contain data"
        )

    vectors: list[list[float]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise LMStudioEmbeddingRequestError(
                f"LM Studio embedding data[{index}] must be an object"
            )
        vectors.append(_vector_from_raw(item.get("embedding")))
    return vectors


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
    payload = _post_json(
        f"{normalized_base_url}/embeddings",
        {"model": model, "input": texts},
        timeout=timeout,
    )
    return _extract_vectors(payload)


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
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
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
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
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
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> QueryEmbedding:
    """Embed a question with the model policy required by an installed pack."""
    return embed_question_with_spec(
        question,
        embedding_spec_for_pack(installed_pack),
        base_url=base_url,
        timeout=timeout,
    )
