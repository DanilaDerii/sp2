"""Pack file writer for pack.json, chunks.json, and vectors.npy."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .embedder import EmbeddedChunk

DEFAULT_TUTOR_MODE = "debug"
DEFAULT_TOP_K = 5
DEFAULT_BUILDER_VERSION = "v1-prototype"


@dataclass(slots=True)
class PackMetadata:
    """Metadata written into pack.json for an exported pack."""

    pack_id: str
    title: str
    version: str
    description: str
    embedding_model: str
    embedding_dim: int
    tutor_mode: str
    default_top_k: int
    created_at: str
    builder_version: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in a compact ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _chunk_records(embedded_chunks: list[EmbeddedChunk]) -> list[dict[str, Any]]:
    """Convert embedded chunks into chunks.json records."""
    return [
        {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "source_type": chunk.source_type,
            "source_title": chunk.source_title,
            "text": chunk.text,
            "chunk_index": chunk.chunk_index,
            "page": chunk.page,
            "section": chunk.section,
            "topic": chunk.topic,
            "char_count": chunk.char_count,
        }
        for chunk in embedded_chunks
    ]


def _vector_matrix(embedded_chunks: list[EmbeddedChunk]) -> np.ndarray:
    """Convert embedded chunk vectors into a stable float32 matrix."""
    return np.asarray([chunk.vector for chunk in embedded_chunks], dtype=np.float32)


def build_pack_metadata(
    *,
    pack_id: str,
    title: str,
    version: str,
    description: str,
    embedding_model: str,
    embedding_dim: int,
    tutor_mode: str = DEFAULT_TUTOR_MODE,
    default_top_k: int = DEFAULT_TOP_K,
    builder_version: str = DEFAULT_BUILDER_VERSION,
) -> PackMetadata:
    """Construct the normalized metadata object for pack.json."""
    return PackMetadata(
        pack_id=pack_id,
        title=title,
        version=version,
        description=description,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        tutor_mode=tutor_mode,
        default_top_k=default_top_k,
        created_at=_utc_now_iso(),
        builder_version=builder_version,
    )


def write_pack_directory(
    output_dir: str | Path,
    *,
    metadata: PackMetadata,
    embedded_chunks: list[EmbeddedChunk],
) -> dict[str, str]:
    """Write the v1 pack files into a directory and return their paths."""
    output_path = Path(output_dir).expanduser().resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    vectors = _vector_matrix(embedded_chunks)
    if len(embedded_chunks) > 0 and vectors.shape[1] != metadata.embedding_dim:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"metadata={metadata.embedding_dim}, vectors={vectors.shape[1]}"
        )

    pack_json_path = output_path / "pack.json"
    chunks_json_path = output_path / "chunks.json"
    vectors_npy_path = output_path / "vectors.npy"

    with pack_json_path.open("w", encoding="utf-8") as file:
        json.dump(asdict(metadata), file, indent=2)

    with chunks_json_path.open("w", encoding="utf-8") as file:
        json.dump(_chunk_records(embedded_chunks), file, indent=2)

    np.save(vectors_npy_path, vectors)

    return {
        "pack_json": str(pack_json_path),
        "chunks_json": str(chunks_json_path),
        "vectors_npy": str(vectors_npy_path),
    }
