"""PDF-specific teacher-side RAG pipeline orchestrator."""

from pathlib import Path

from ..common.chunker import chunk_extracted_document
from ..common.embedder import DEFAULT_EMBEDDING_MODEL, embed_chunks
from ..common.models import TeacherPipelineResult
from ...orchestrators.artifact_manager import ARTIFACTS_DIR, prepare_teacher_artifacts
from ...orchestrators.pack_writer import (
    DEFAULT_BUILDER_VERSION,
    DEFAULT_TOP_K,
    build_pack_metadata,
    write_pack_directory,
)
from ...orchestrators.zip_exporter import export_pack_zip
from .extractor import extract_pdf_text


def _default_pack_id(source_path: Path) -> str:
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


def _default_pack_title(source_path: Path) -> str:
    """Derive a user-facing title from the source filename."""
    return source_path.stem.strip() or source_path.name


def build_pack_from_pdf(
    pdf_path: str | Path,
    *,
    output_dir: str | Path | None = None,
    zip_path: str | Path | None = None,
    pack_id: str | None = None,
    title: str | None = None,
    version: str = "v1",
    description: str = "",
    source_type: str = "pdf",
    chunk_size: int = 1200,
    overlap: int = 150,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL,
    default_top_k: int = DEFAULT_TOP_K,
    builder_version: str = DEFAULT_BUILDER_VERSION,
    artifacts_dir: str | Path = ARTIFACTS_DIR,
    rewrite_existing: bool = True,
) -> TeacherPipelineResult:
    """Run the current v1 teacher pipeline for one PDF source."""
    source_path = Path(pdf_path).expanduser().resolve()
    resolved_pack_id = pack_id or _default_pack_id(source_path)

    if output_dir is None or zip_path is None:
        if output_dir is not None or zip_path is not None:
            raise ValueError("output_dir and zip_path must be provided together")
        artifact_paths = prepare_teacher_artifacts(
            resolved_pack_id,
            artifacts_dir=artifacts_dir,
            rewrite_existing=rewrite_existing,
        )
        output_dir = artifact_paths.pack_dir
        zip_path = artifact_paths.zip_path

    extracted_document = extract_pdf_text(source_path)
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
        title=title or _default_pack_title(source_path),
        version=version,
        description=description,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        default_top_k=default_top_k,
        builder_version=builder_version,
    )
    written_paths = write_pack_directory(
        output_dir,
        metadata=metadata,
        embedded_chunks=embedded_chunks,
    )
    exported_zip_path = export_pack_zip(output_dir, zip_path)

    return TeacherPipelineResult(
        extracted_document=extracted_document,
        chunks=chunks,
        embedded_chunks=embedded_chunks,
        metadata=metadata,
        pack_directory=str(Path(output_dir).expanduser().resolve()),
        pack_json_path=written_paths["pack_json"],
        chunks_json_path=written_paths["chunks_json"],
        vectors_npy_path=written_paths["vectors_npy"],
        zip_path=exported_zip_path,
    )
