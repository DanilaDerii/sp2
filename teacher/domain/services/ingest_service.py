"""Teacher ingest service layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from teacher.domain.rag.common.models import TeacherPipelineResult
from teacher.domain.rag.pdf.pipeline import build_pack_from_pdf


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


def ingest_pdf_from_path(pdf_path: str | Path) -> TeacherIngestResult:
    """Build a teacher pack from one PDF path and return an API-ready summary."""
    result = build_pack_from_pdf(pdf_path)
    return _teacher_ingest_result(result)
