"""Student-side pack import workflow."""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from backend.core.paths import PACKS_DIR, ensure_runtime_dirs
from backend.storage.lancedb import insert_chunks
from backend.storage.sqlite import create_installed_pack, initialize_database


REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")


@dataclass(slots=True)
class ImportedPack:
    """Summary of a completed student-side pack import."""

    installed_pack_id: int
    pack_id: str
    title: str
    version: str
    install_path: str
    chunk_count: int
    embedding_dim: int


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in a compact ISO format."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load_json(path: Path) -> dict | list:
    """Load a UTF-8 JSON file from disk."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalize_chunk_records(
    pack_id: str,
    chunks: list[dict],
    vectors: np.ndarray,
) -> list[dict]:
    """Merge chunks.json rows with vectors.npy rows for LanceDB import."""
    if len(chunks) != len(vectors):
        raise ValueError(
            "Chunk/vector count mismatch: "
            f"{len(chunks)} chunks vs {len(vectors)} vectors"
        )

    records: list[dict] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        page = chunk.get("page")
        records.append(
            {
                "chunk_id": chunk["chunk_id"],
                "pack_id": pack_id,
                "source_id": chunk["source_id"],
                "source_type": chunk["source_type"],
                "source_title": chunk["source_title"],
                "text": chunk["text"],
                "vector": vector.tolist(),
                "chunk_index": int(chunk["chunk_index"]),
                "page": None if page is None else str(page),
                "section": chunk.get("section"),
                "topic": chunk.get("topic"),
            }
        )

    return records


def _extract_zip(zip_path: Path, destination_dir: Path) -> None:
    """Extract a pack zip into its installed pack directory."""
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path) as zip_file:
        zip_file.extractall(destination_dir)


def import_pack_zip(zip_path: str | Path) -> ImportedPack:
    """Import a teacher-built pack zip into local student runtime storage."""
    ensure_runtime_dirs()
    initialize_database()

    source_zip_path = Path(zip_path).expanduser().resolve()
    if not source_zip_path.exists():
        raise FileNotFoundError(f"Pack zip not found: {source_zip_path}")
    if not source_zip_path.is_file():
        raise ValueError(f"Expected a zip file, got: {source_zip_path}")

    temp_extract_dir = PACKS_DIR / f".tmp-{source_zip_path.stem}"
    _extract_zip(source_zip_path, temp_extract_dir)

    missing_files = [
        file_name for file_name in REQUIRED_PACK_FILES if not (temp_extract_dir / file_name).exists()
    ]
    if missing_files:
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        raise FileNotFoundError(
            "Imported pack is missing required files: " + ", ".join(missing_files)
        )

    pack_metadata = _load_json(temp_extract_dir / "pack.json")
    if not isinstance(pack_metadata, dict):
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        raise ValueError("pack.json must contain a JSON object")

    chunks = _load_json(temp_extract_dir / "chunks.json")
    if not isinstance(chunks, list):
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        raise ValueError("chunks.json must contain a JSON array")

    vectors = np.load(temp_extract_dir / "vectors.npy")
    if vectors.ndim != 2:
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        raise ValueError("vectors.npy must be a 2D matrix")

    pack_id = str(pack_metadata["pack_id"])
    version = str(pack_metadata["version"])
    title = str(pack_metadata["title"])
    install_dir = PACKS_DIR / f"{pack_id}-{version}"

    if install_dir.exists():
        shutil.rmtree(install_dir)
    temp_extract_dir.rename(install_dir)

    embedding_dim = int(pack_metadata["embedding_dim"])
    if len(chunks) > 0 and vectors.shape[1] != embedding_dim:
        raise ValueError(
            "Pack metadata embedding_dim does not match vectors.npy width: "
            f"{embedding_dim} vs {vectors.shape[1]}"
        )

    chunk_records = _normalize_chunk_records(pack_id, chunks, vectors)
    if chunk_records:
        insert_chunks(chunk_records, embedding_dim)

    installed_pack_id = create_installed_pack(
        pack_id=pack_id,
        title=title,
        version=version,
        install_path=str(install_dir),
        installed_at=_utc_now_iso(),
        is_active=True,
    )

    return ImportedPack(
        installed_pack_id=installed_pack_id,
        pack_id=pack_id,
        title=title,
        version=version,
        install_path=str(install_dir),
        chunk_count=len(chunk_records),
        embedding_dim=embedding_dim,
    )
