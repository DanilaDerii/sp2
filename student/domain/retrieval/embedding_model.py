"""Embedding model policy for student retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from student.storage.cruds.sqlite.pack_repository import InstalledPack


DEFAULT_QUERY_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"


class EmbeddingModelError(RuntimeError):
    """Raised when retrieval embedding model selection is invalid."""


class EmbeddingModelMismatchError(EmbeddingModelError):
    """Raised when an installed pack was built with a different embedding model."""


@dataclass(frozen=True, slots=True)
class EmbeddingModelSpec:
    """Embedding model selected for student-side query retrieval."""

    model: str
    expected_dim: int | None = None


def default_query_embedding_spec() -> EmbeddingModelSpec:
    """Return the fixed v1 query embedding model policy."""
    return EmbeddingModelSpec(model=DEFAULT_QUERY_EMBEDDING_MODEL)


def embedding_spec_for_pack(installed_pack: InstalledPack) -> EmbeddingModelSpec:
    """Return the query embedding model required for an installed pack.

    V1 only supports the fixed default model. This function keeps the policy in
    one place so later dynamic model switching can be added without rewriting the
    embedding or retrieval modules.
    """
    if installed_pack.embedding_model != DEFAULT_QUERY_EMBEDDING_MODEL:
        raise EmbeddingModelMismatchError(
            "Installed pack embedding model does not match the student query embedder: "
            f"pack={installed_pack.embedding_model!r}, query={DEFAULT_QUERY_EMBEDDING_MODEL!r}"
        )

    return EmbeddingModelSpec(
        model=installed_pack.embedding_model,
        expected_dim=installed_pack.embedding_dim,
    )
