"""Teacher backend service boundaries."""

from .ingest_service import TeacherIngestResult, ingest_path_to_file

__all__ = ["TeacherIngestResult", "ingest_path_to_file"]
