"""Main Runner. Orchestrate teacher source ingestion into an exported course pack."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from config.arguments import (
    ARTIFACTS_DIR,
    DEFAULT_BUILDER_VERSION,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
)
from teacher.domain.orchestrators.artifact_manager import (
    prepare_zip_destination,
    teacher_artifact_zip_path,
)
from teacher.domain.orchestrators.pack_writer import (
    build_pack_metadata,
    write_pack_directory,
)
from teacher.domain.orchestrators.zip_exporter import export_pack_zip
from teacher.domain.rag.common.chunker import chunk_extracted_document
from teacher.domain.rag.common.embedder import embed_chunks
from teacher.domain.rag.common.models import ExtractedDocument, TeacherPipelineResult


ExtractDocument = Callable[[str | Path], ExtractedDocument]


def default_pack_id(source_path: Path) -> str:
    """Derive a simple v1 pack id from the source filename."""
    safe_chars: list[str] = []
    previous_was_separator = False

    for char in source_path.stem.strip().lower():
        if char.isalnum() or char == "_":
            safe_chars.append(char)
            previous_was_separator = False
        elif not previous_was_separator:
            safe_chars.append("-")
            previous_was_separator = True

    safe_id = "".join(safe_chars).strip("-_")
    return safe_id or "sp2-pack"


def default_pack_title(source_path: Path) -> str:
    """Derive a user-facing title from the source filename."""
    return source_path.stem.strip() or source_path.name


def build_pack_from_source(
    source_file_path: str | Path,
    *,
    extract_document: ExtractDocument,
    source_type: str,
    zip_path: str | Path | None = None,
    pack_id: str | None = None,
    title: str | None = None,
    version: str = "v1",
    description: str = "",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    default_top_k: int = DEFAULT_TOP_K,
    builder_version: str = DEFAULT_BUILDER_VERSION,
    artifacts_dir: str | Path = ARTIFACTS_DIR,
    rewrite_existing: bool = True,
) -> TeacherPipelineResult:
    """Run the current v1 teacher pipeline for one extracted source type."""
    source_path = Path(source_file_path).expanduser().resolve()
    resolved_pack_id = pack_id or default_pack_id(source_path)
    requested_zip_path = zip_path or teacher_artifact_zip_path(
        resolved_pack_id,
        artifacts_dir=artifacts_dir,
    )
    final_zip_path = prepare_zip_destination(
        requested_zip_path,
        rewrite_existing=rewrite_existing,
    )

    extracted_document = extract_document(source_path)
    chunks = chunk_extracted_document(
        extracted_document,
        source_id=resolved_pack_id,
        source_type=source_type,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    embedded_chunks = embed_chunks(
        chunks,
        model=embedding_model,
    )

    embedding_dim = len(embedded_chunks[0].vector) if embedded_chunks else 0
    metadata = build_pack_metadata(
        pack_id=resolved_pack_id,
        title=title or default_pack_title(source_path),
        version=version,
        description=description,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        default_top_k=default_top_k,
        builder_version=builder_version,
    )
    with TemporaryDirectory(
        dir=final_zip_path.parent,
        prefix=f".{final_zip_path.stem}-",
    ) as temporary_dir:
        staging_root = Path(temporary_dir)
        staging_pack_dir = staging_root / "pack"
        staging_zip_path = staging_root / final_zip_path.name

        write_pack_directory(
            staging_pack_dir,
            metadata=metadata,
            embedded_chunks=embedded_chunks,
        )
        export_pack_zip(staging_pack_dir, staging_zip_path)
        staging_zip_path.replace(final_zip_path)

    return TeacherPipelineResult(
        source_path=extracted_document.source_path,
        page_count=extracted_document.page_count,
        chunk_count=len(chunks),
        metadata=metadata,
        zip_path=str(final_zip_path),
    )
