"""Build one course pack from a supported file or directory tree."""

from __future__ import annotations

from pathlib import Path

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
from teacher.domain.orchestrators.bundle_parsing.bundle_parser_helper import (
    _SOURCE_EXTRACTORS,
    _default_pack_id,
    _default_pack_title,
    _discover_supported_files,
    _embedding_dimension,
    _extractor_for_path,
    _finalize_pack,
    _resolve_source_path,
    _source_id_for_path,
)
from teacher.domain.orchestrators.pack_writer import (
    build_pack_metadata,
)
from teacher.domain.rag.common.chunker import chunk_extracted_document
from teacher.domain.rag.common.embedder import embed_chunks
from teacher.domain.rag.common.models import (
    EmbeddedChunk,
    TeacherPipelineResult,
)


def build_pack_from_path(
    source_path: str | Path,
    *,
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
    """Build one pack from an exact file or all supported files in a directory."""
    selected_path = _resolve_source_path(source_path)
    source_files = _discover_supported_files(selected_path)
    if not source_files:
        supported = ", ".join(_SOURCE_EXTRACTORS)
        raise ValueError(
            f"Directory contains no supported source files: {selected_path}. "
            f"Supported file types: {supported}"
        )

    resolved_pack_id = pack_id or _default_pack_id(selected_path)
    resolved_title = title or _default_pack_title(selected_path)
    requested_zip_path = zip_path or teacher_artifact_zip_path(
        resolved_pack_id,
        artifacts_dir=artifacts_dir,
    )
    final_zip_path = prepare_zip_destination(
        requested_zip_path,
        rewrite_existing=rewrite_existing,
    )

    embedded_chunks: list[EmbeddedChunk] = []
    total_page_count = 0

    for source_file in source_files:
        source_type, extract_document = _extractor_for_path(source_file)
        extracted_document = extract_document(source_file)
        chunks = chunk_extracted_document(
            extracted_document,
            source_id=_source_id_for_path(selected_path, source_file),
            source_type=source_type,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        embedded_chunks.extend(
            embed_chunks(
                chunks,
                model=embedding_model,
            )
        )
        total_page_count += extracted_document.page_count

    embedding_dim = _embedding_dimension(embedded_chunks)
    metadata = build_pack_metadata(
        pack_id=resolved_pack_id,
        title=resolved_title,
        version=version,
        description=description,
        embedding_model=embedding_model,
        embedding_dim=embedding_dim,
        default_top_k=default_top_k,
        builder_version=builder_version,
    )
    _finalize_pack(
        embedded_chunks=embedded_chunks,
        metadata=metadata,
        final_zip_path=final_zip_path,
    )

    return TeacherPipelineResult(
        source_path=str(selected_path),
        page_count=total_page_count,
        chunk_count=len(embedded_chunks),
        metadata=metadata,
        zip_path=str(final_zip_path),
    )
