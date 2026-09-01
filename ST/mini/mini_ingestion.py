"""Standalone reduced SP2 PDF-ingestion model for software testing.

The normal SP2 setup/cleanup script is expected to initialize SQLite and LanceDB.
"""

import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
INSTALLED_PACKS_DIR = REPO_ROOT / "storage" / "installed_packs"
SQLITE_DB_PATH = REPO_ROOT / "storage" / "database" / "sqlite_storage" / "student_app.db"
LANCE_DB_PATH = REPO_ROOT / "storage" / "database" / "lance_storage"

EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
EMBEDDING_DIMENSION = 768
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_OVERLAP = 150
DEFAULT_TOP_K = 5
REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")

Embedder = Callable[..., list[list[float]]]


@dataclass(frozen=True, slots=True)
class MiniChunk:
    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int
    section: str | None


@dataclass(frozen=True, slots=True)
class MiniEmbeddedChunk:
    chunk: MiniChunk
    vector: list[float]


@dataclass(frozen=True, slots=True)
class MiniIngestionResult:
    installed_pack_id: int
    pack_id: str
    title: str
    version: str
    chunk_count: int
    embedding_model: str
    embedding_dimension: int
    zip_path: str
    install_path: str


def _pack_is_installed(pack_id: str, version: str, install_path: Path) -> bool:
    """Read the two duplicate indicators used by the mini pipeline."""
    with closing(sqlite3.connect(SQLITE_DB_PATH)) as connection:
        database_match = connection.execute(
            "SELECT 1 FROM installed_packs WHERE pack_id = ? AND version = ?",
            (pack_id, version),
        ).fetchone()
    return database_match is not None or install_path.exists()


def _export_pack_zip(
    metadata: dict[str, object],
    chunk_records: list[dict[str, object]],
    vector_rows: list[list[float]],
    zip_path: Path,
) -> None:
    """Write, minimally validate, and ZIP the portable three-file pack."""
    import numpy as np

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    vector_matrix = np.asarray(vector_rows, dtype=np.float32)

    with TemporaryDirectory(prefix="sp2-mini-pack-") as temporary_directory:
        pack_path = Path(temporary_directory)
        with (pack_path / "pack.json").open("w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2)
        with (pack_path / "chunks.json").open("w", encoding="utf-8") as file:
            json.dump(chunk_records, file, indent=2)
        np.save(pack_path / "vectors.npy", vector_matrix)

        for required_file in REQUIRED_PACK_FILES:
            if not (pack_path / required_file).is_file():
                raise ValueError(f"pack is missing {required_file}")

        with (pack_path / "pack.json").open(encoding="utf-8") as file:
            stored_metadata = json.load(file)
        with (pack_path / "chunks.json").open(encoding="utf-8") as file:
            stored_chunks = json.load(file)
        stored_vectors = np.load(pack_path / "vectors.npy", allow_pickle=False)

        expected_shape = (len(chunk_records), metadata["embedding_dim"])
        if stored_metadata.get("embedding_dim") != metadata["embedding_dim"]:
            raise ValueError("pack metadata has the wrong embedding dimension")
        if len(stored_chunks) != len(chunk_records) or stored_vectors.shape != expected_shape:
            raise ValueError("pack chunk and vector counts do not match")

        with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
            for required_file in REQUIRED_PACK_FILES:
                archive.write(pack_path / required_file, arcname=required_file)


def _install_pack_files(zip_path: Path, install_path: Path) -> None:
    """Extract only the three pack files into the real installed-pack directory."""
    install_path.parent.mkdir(parents=True, exist_ok=True)
    install_path.mkdir()
    with ZipFile(zip_path) as archive:
        for required_file in REQUIRED_PACK_FILES:
            archive.extract(required_file, install_path)


def _insert_sqlite_metadata(
    metadata: dict[str, object],
    install_path: Path,
) -> int:
    """Insert the installed-pack record and return its local primary key."""
    installed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with closing(sqlite3.connect(SQLITE_DB_PATH)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO installed_packs (
                    pack_id, title, version, description, embedding_model,
                    embedding_dim, default_top_k, builder_version,
                    pack_created_at, install_path, installed_at, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["pack_id"],
                    metadata["title"],
                    metadata["version"],
                    metadata["description"],
                    metadata["embedding_model"],
                    metadata["embedding_dim"],
                    metadata["default_top_k"],
                    metadata["builder_version"],
                    metadata["created_at"],
                    str(install_path),
                    installed_at,
                    1,
                ),
            )
            return int(cursor.lastrowid)


def _insert_lancedb_chunks(
    embedded_chunks: list[MiniEmbeddedChunk],
    installed_pack_id: int,
    pack_id: str,
) -> int:
    """Insert searchable chunk/vector rows and return their stored count."""
    import lancedb

    database = lancedb.connect(LANCE_DB_PATH)
    table = database.open_table("pack_chunks")
    rows: list[dict[str, object]] = []

    for embedded_chunk in embedded_chunks:
        chunk = embedded_chunk.chunk
        rows.append(
            {
                "chunk_id": chunk.chunk_id,
                "installed_pack_id": installed_pack_id,
                "pack_id": pack_id,
                "source_id": chunk.source_id,
                "source_type": chunk.source_type,
                "source_title": chunk.source_title,
                "text": chunk.text,
                "vector": embedded_chunk.vector,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "section": chunk.section,
            }
        )

    table.add(rows)
    return table.count_rows(f"installed_pack_id = {installed_pack_id}")


def _open_pdf(source: Path):
    """Open the PDF through the external PyMuPDF boundary."""
    import pymupdf

    return pymupdf.open(str(source))


def mini_ingest_pdf(
    pdf_path: str | Path,
    *,
    pack_id: str,
    title: str,
    embedder: Embedder,
    version: str = "v1",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    embedding_model: str = EMBEDDING_MODEL,
) -> MiniIngestionResult:
    """Ingest one PDF using the core decisions and state changes of SP2."""
    source = Path(pdf_path).expanduser().resolve()
    pack_id = pack_id.strip()
    title = title.strip()
    version = version.strip()
    embedding_model = embedding_model.strip()

    # 1. Validate the input domains.
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ValueError("pdf_path must point to an existing PDF file")
    if not pack_id or not title or not version or not embedding_model:
        raise ValueError("pack_id, title, version, and embedding_model are required")
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("require chunk_size > 0 and 0 <= overlap < chunk_size")

    safe_name_characters: list[str] = []
    for character in f"{pack_id}-{version}":
        if character.isalnum() or character in {"-", "_"}:
            safe_name_characters.append(character)
        else:
            safe_name_characters.append("-")
    install_name = "".join(safe_name_characters).strip("-_")
    install_path = INSTALLED_PACKS_DIR / install_name
    if not install_name:
        raise ValueError("pack_id and version must contain a usable name")

    # 2. Reject a duplicate before extraction or embedding.
    if _pack_is_installed(pack_id, version, install_path):
        raise FileExistsError(f"pack is already installed: {pack_id} {version}")

    # 3. Extract PDF pages. PyMuPDF is the document-extraction boundary.
    pages: list[tuple[int, str]] = []
    with _open_pdf(source) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            page_text = page.get_text("text", sort=True).strip()
            pages.append((page_number, page_text))

    # 4. Create overlapping character chunks and retain source metadata.
    chunks: list[MiniChunk] = []
    chunk_index = 0
    for page_number, page_text in pages:
        normalized_text = " ".join(page_text.split()).strip()
        if not normalized_text:
            continue

        section = None
        for line in page_text.splitlines():
            normalized_line = " ".join(line.split()).strip()
            if normalized_line:
                section = normalized_line[:160]
                break

        start = 0
        while start < len(normalized_text):
            end = min(start + chunk_size, len(normalized_text))
            chunks.append(
                MiniChunk(
                    chunk_id=f"{source.name}::chunk::{chunk_index}",
                    source_id=source.name,
                    source_type="pdf",
                    source_title=source.name,
                    text=normalized_text[start:end],
                    chunk_index=chunk_index,
                    page=page_number,
                    section=section,
                )
            )
            chunk_index += 1
            if end == len(normalized_text):
                break
            start = end - overlap

    if not chunks:
        raise ValueError("PDF produced no searchable chunks")

    # 5. Build embedding inputs and call the external embedding black box.
    document_inputs: list[str] = []
    for chunk in chunks:
        document_inputs.append(f"search_document: {chunk.text}")

    vectors = embedder(document_inputs, model=embedding_model)
    if len(vectors) != len(chunks):
        raise ValueError("embedding count must equal chunk count")

    embedding_dimension = len(vectors[0])
    if embedding_dimension != EMBEDDING_DIMENSION:
        raise ValueError(f"embedding dimension must be {EMBEDDING_DIMENSION}")
    for vector in vectors:
        if len(vector) != embedding_dimension:
            raise ValueError("all embeddings must have the same dimension")

    embedded_chunks: list[MiniEmbeddedChunk] = []
    for index in range(len(chunks)):
        embedded_chunks.append(
            MiniEmbeddedChunk(chunk=chunks[index], vector=vectors[index])
        )

    # 6. Create portable pack data from the chunks and vectors.
    created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    metadata: dict[str, object] = {
        "pack_id": pack_id,
        "title": title,
        "version": version,
        "description": "",
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dimension,
        "default_top_k": DEFAULT_TOP_K,
        "created_at": created_at,
        "builder_version": "mini-v1",
    }

    chunk_records: list[dict[str, object]] = []
    vector_rows: list[list[float]] = []
    for embedded_chunk in embedded_chunks:
        chunk = embedded_chunk.chunk
        chunk_records.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "source_type": chunk.source_type,
                "source_title": chunk.source_title,
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "page": chunk.page,
                "section": chunk.section,
            }
        )
        vector_rows.append(embedded_chunk.vector)

    # 7. Export, install, and persist the pack through local same-file boundaries.
    zip_path = ARTIFACTS_DIR / f"{install_name}.zip"
    _export_pack_zip(metadata, chunk_records, vector_rows, zip_path)
    _install_pack_files(zip_path, install_path)
    installed_pack_id = _insert_sqlite_metadata(metadata, install_path)
    stored_chunk_count = _insert_lancedb_chunks(
        embedded_chunks,
        installed_pack_id,
        pack_id,
    )
    if stored_chunk_count != len(chunks):
        raise ValueError("LanceDB stored a different number of chunks")

    return MiniIngestionResult(
        installed_pack_id=installed_pack_id,
        pack_id=pack_id,
        title=title,
        version=version,
        chunk_count=stored_chunk_count,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        zip_path=str(zip_path),
        install_path=str(install_path),
    )
