"""Validation helpers for portable teacher pack artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")


class PackValidationError(ValueError):
    """Raised when a teacher pack does not match the student import contract."""


@dataclass(frozen=True, slots=True)
class PackMetadata:
    """Validated metadata loaded from pack.json."""

    pack_id: str
    title: str
    version: str
    description: str | None
    embedding_model: str
    embedding_dim: int
    default_top_k: int
    created_at: str
    builder_version: str | None


@dataclass(frozen=True, slots=True)
class PackChunkRecord:
    """Validated chunk metadata loaded from chunks.json."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None
    topic: str | None
    char_count: int


@dataclass(frozen=True, slots=True)
class ValidatedPack:
    """Fully validated pack files ready for import into student storage."""

    pack_dir: Path
    metadata: PackMetadata
    chunks: list[PackChunkRecord]
    vectors: Any


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise PackValidationError(f"Invalid JSON file: {path.name}") from exc


def _require_string(data: dict[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise PackValidationError(f"pack.json field must be a non-empty string: {field_name}")
    return value


def _optional_string(data: dict[str, Any], field_name: str) -> str | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PackValidationError(f"pack.json field must be a string or null: {field_name}")
    return value


def _require_positive_int(data: dict[str, Any], field_name: str) -> int:
    value = data.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PackValidationError(f"pack.json field must be a positive integer: {field_name}")
    return value


def _validate_metadata(raw_metadata: Any) -> PackMetadata:
    if not isinstance(raw_metadata, dict):
        raise PackValidationError("pack.json must contain a JSON object")

    return PackMetadata(
        pack_id=_require_string(raw_metadata, "pack_id"),
        title=_require_string(raw_metadata, "title"),
        version=_require_string(raw_metadata, "version"),
        description=_optional_string(raw_metadata, "description"),
        embedding_model=_require_string(raw_metadata, "embedding_model"),
        embedding_dim=_require_positive_int(raw_metadata, "embedding_dim"),
        default_top_k=_require_positive_int(raw_metadata, "default_top_k"),
        created_at=_require_string(raw_metadata, "created_at"),
        builder_version=_optional_string(raw_metadata, "builder_version"),
    )


def _require_chunk_string(data: dict[str, Any], field_name: str, index: int) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise PackValidationError(
            f"chunks.json[{index}] field must be a non-empty string: {field_name}"
        )
    return value


def _require_chunk_int(data: dict[str, Any], field_name: str, index: int) -> int:
    value = data.get(field_name)
    if not isinstance(value, int) or isinstance(value, bool):
        raise PackValidationError(f"chunks.json[{index}] field must be an integer: {field_name}")
    return value


def _optional_chunk_int(data: dict[str, Any], field_name: str, index: int) -> int | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise PackValidationError(
            f"chunks.json[{index}] field must be an integer or null: {field_name}"
        )
    return value


def _optional_chunk_string(data: dict[str, Any], field_name: str, index: int) -> str | None:
    value = data.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise PackValidationError(
            f"chunks.json[{index}] field must be a string or null: {field_name}"
        )
    return value


def _validate_chunks(raw_chunks: Any) -> list[PackChunkRecord]:
    if not isinstance(raw_chunks, list):
        raise PackValidationError("chunks.json must contain a JSON array")

    chunks: list[PackChunkRecord] = []
    seen_chunk_ids: set[str] = set()

    for index, raw_chunk in enumerate(raw_chunks):
        if not isinstance(raw_chunk, dict):
            raise PackValidationError(f"chunks.json[{index}] must contain a JSON object")

        chunk_id = _require_chunk_string(raw_chunk, "chunk_id", index)
        if chunk_id in seen_chunk_ids:
            raise PackValidationError(f"Duplicate chunk_id in chunks.json: {chunk_id}")
        seen_chunk_ids.add(chunk_id)

        text = _require_chunk_string(raw_chunk, "text", index)
        raw_char_count = raw_chunk.get("char_count")
        if raw_char_count is None:
            char_count = len(text)
        elif isinstance(raw_char_count, int) and not isinstance(raw_char_count, bool):
            char_count = raw_char_count
        else:
            raise PackValidationError(
                f"chunks.json[{index}] field must be an integer or null: char_count"
            )

        chunks.append(
            PackChunkRecord(
                chunk_id=chunk_id,
                source_id=_require_chunk_string(raw_chunk, "source_id", index),
                source_type=_require_chunk_string(raw_chunk, "source_type", index),
                source_title=_require_chunk_string(raw_chunk, "source_title", index),
                text=text,
                chunk_index=_require_chunk_int(raw_chunk, "chunk_index", index),
                page=_optional_chunk_int(raw_chunk, "page", index),
                section=_optional_chunk_string(raw_chunk, "section", index),
                topic=_optional_chunk_string(raw_chunk, "topic", index),
                char_count=char_count,
            )
        )

    return chunks


def _load_vectors(path: Path):
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise RuntimeError("NumPy is required to validate vectors.npy") from exc

    try:
        return np.load(path, allow_pickle=False)
    except ValueError as exc:
        raise PackValidationError("vectors.npy must be a non-pickled NumPy array") from exc


def _validate_vectors(vectors: Any, chunks: list[PackChunkRecord], metadata: PackMetadata) -> None:
    if len(chunks) == 0:
        raise PackValidationError("chunks.json must contain at least one chunk")

    if getattr(vectors, "ndim", None) != 2:
        raise PackValidationError("vectors.npy must contain a 2D vector matrix")

    if vectors.shape[0] != len(chunks):
        raise PackValidationError(
            "Vector count mismatch: "
            f"chunks={len(chunks)}, vectors={vectors.shape[0]}"
        )

    if vectors.shape[1] != metadata.embedding_dim:
        raise PackValidationError(
            "Embedding dimension mismatch: "
            f"metadata={metadata.embedding_dim}, vectors={vectors.shape[1]}"
        )


def validate_pack_directory(pack_dir: str | Path) -> ValidatedPack:
    """Validate an unpacked teacher pack directory."""
    resolved_pack_dir = Path(pack_dir).expanduser().resolve()
    if not resolved_pack_dir.exists():
        raise FileNotFoundError(f"Pack directory not found: {resolved_pack_dir}")
    if not resolved_pack_dir.is_dir():
        raise PackValidationError(f"Expected pack directory, got file: {resolved_pack_dir}")

    missing_files = [
        file_name for file_name in REQUIRED_PACK_FILES if not (resolved_pack_dir / file_name).is_file()
    ]
    if missing_files:
        raise PackValidationError(
            "Pack directory is missing required files: " + ", ".join(missing_files)
        )

    metadata = _validate_metadata(_read_json(resolved_pack_dir / "pack.json"))
    chunks = _validate_chunks(_read_json(resolved_pack_dir / "chunks.json"))
    vectors = _load_vectors(resolved_pack_dir / "vectors.npy")
    _validate_vectors(vectors, chunks, metadata)

    return ValidatedPack(
        pack_dir=resolved_pack_dir,
        metadata=metadata,
        chunks=chunks,
        vectors=vectors,
    )
