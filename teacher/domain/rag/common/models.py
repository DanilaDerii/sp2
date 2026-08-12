"""Shared data models for teacher-side pack building."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExtractedPage:
    """Extracted text for one page or page-like source unit."""

    page_number: int
    text: str


@dataclass(slots=True)
class ExtractedDocument:
    """Normalized extraction result returned by a source extractor."""

    source_path: str
    page_count: int
    pages: list[ExtractedPage]

    @property
    def source_name(self) -> str:
        """Return the source filename derived from the source path."""
        return Path(self.source_path).name


@dataclass(slots=True)
class ChunkedText:
    """One retrieval-ready text chunk with basic source metadata."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None


@dataclass(slots=True)
class EmbeddedChunk:
    """Chunk data paired with its embedding vector."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    vector: list[float]
    chunk_index: int
    page: int | None
    section: str | None


@dataclass(slots=True)
class PackMetadata:
    """Metadata written into pack.json for an exported pack."""

    pack_id: str
    title: str
    version: str
    description: str
    embedding_model: str
    embedding_dim: int
    default_top_k: int
    created_at: str
    builder_version: str


@dataclass(slots=True)
class TeacherPipelineResult:
    """Outputs produced by the teacher-side v1 build pipeline."""

    source_path: str
    page_count: int
    chunk_count: int
    metadata: PackMetadata
    zip_path: str
