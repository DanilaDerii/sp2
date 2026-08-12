"""Import teacher source files into the pack-building pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.arguments import SUPPORTED_SOURCE_SUFFIXES
from teacher.domain.rag.common.models import TeacherPipelineResult
from teacher.domain.orchestrators.pack_pipeline import build_pack_from_source
from teacher.domain.rag.doc.docx.extractor import extract_docx_text
from teacher.domain.rag.doc.odt.extractor import extract_odt_text
from teacher.domain.rag.pdf.extractor import extract_pdf_text

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
    zip_path: str


def _teacher_ingest_result(result: TeacherPipelineResult) -> TeacherIngestResult:
    return TeacherIngestResult(
        source_path=result.source_path,
        pack_id=result.metadata.pack_id,
        title=result.metadata.title,
        page_count=result.page_count,
        chunk_count=result.chunk_count,
        embedding_model=result.metadata.embedding_model,
        embedding_dim=result.metadata.embedding_dim,
        zip_path=result.zip_path,
    )


def ingest_path_to_file(file_path: str | Path) -> TeacherIngestResult:
    """Build a teacher pack from a supported source path."""
    source_path = Path(file_path).expanduser()
    suffix = source_path.suffix.lower()

    if suffix == ".pdf":
        result = build_pack_from_source(
            source_path,
            extract_document=extract_pdf_text,
            source_type="pdf",
        )
    elif suffix == ".odt":
        result = build_pack_from_source(
            source_path,
            extract_document=extract_odt_text,
            source_type="odt",
        )
    elif suffix == ".docx":
        result = build_pack_from_source(
            source_path,
            extract_document=extract_docx_text,
            source_type="docx",
        )
    else:
        supported = ", ".join(SUPPORTED_SOURCE_SUFFIXES)
        raise ValueError(
            f"Unsupported source file type for {source_path.name!r}. "
            f"Supported file types: {supported}"
        )

    return _teacher_ingest_result(result)
