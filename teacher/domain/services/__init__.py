"""Teacher backend service boundaries."""

from .ingest_service import TeacherIngestResult, ingest_pdf_from_path

__all__ = ["TeacherIngestResult", "ingest_pdf_from_path"]
