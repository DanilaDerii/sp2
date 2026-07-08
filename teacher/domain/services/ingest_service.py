"""Teacher ingest service layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from teacher.domain.rag.common.models import TeacherPipelineResult
from teacher.domain.rag.doc.docx.pipeline import build_pack_from_docx
from teacher.domain.rag.doc.odt.pipeline import build_pack_from_odt
from teacher.domain.rag.pdf.pipeline import build_pack_from_pdf

SUPPORTED_SOURCE_SUFFIXES = (".pdf", ".odt", ".docx")


@dataclass(frozen=True, slots=True)
class TeacherIngestResult:
    """Summary returned after building a teacher pack."""

    source_path: str
    pack_id: str
    title: str
    page_count: int
    chunk_count: int
    embedding_model: str
    embedding_dim: int
    pack_dir: str
    zip_path: str


def _teacher_ingest_result(result: TeacherPipelineResult) -> TeacherIngestResult:
    return TeacherIngestResult(
        source_path=result.extracted_document.source_path,
        pack_id=result.metadata.pack_id,
        title=result.metadata.title,
        page_count=result.extracted_document.page_count,
        chunk_count=len(result.chunks),
        embedding_model=result.metadata.embedding_model,
        embedding_dim=result.metadata.embedding_dim,
        pack_dir=result.pack_directory,
        zip_path=result.zip_path,
    )


def ingest_path_to_file(file_path: str | Path) -> TeacherIngestResult:
    """Build a teacher pack from a supported source path."""
    source_path = Path(file_path).expanduser()
    suffix = source_path.suffix.lower()

    if suffix == ".pdf":
        result = build_pack_from_pdf(source_path)
    elif suffix == ".odt":
        result = build_pack_from_odt(source_path)
    elif suffix == ".docx":
        result = build_pack_from_docx(source_path)
    else:
        supported = ", ".join(SUPPORTED_SOURCE_SUFFIXES)
        raise ValueError(
            f"Unsupported source file type for {source_path.name!r}. "
            f"Supported file types: {supported}"
        )

    return _teacher_ingest_result(result)
