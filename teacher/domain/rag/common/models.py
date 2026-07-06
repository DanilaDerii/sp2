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
    source_name: str
    page_count: int
    text: str
    markdown: str
    pages: list[ExtractedPage]


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
    topic: str | None
    char_count: int


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
    topic: str | None
    char_count: int


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


@dataclass(frozen=True, slots=True)
class TeacherArtifactPaths:
    """Resolved output paths for one generated teacher pack."""

    pack_id: str
    pack_dir: Path
    zip_path: Path


@dataclass(slots=True)
class TeacherPipelineResult:
    """Outputs produced by the teacher-side v1 build pipeline."""

    extracted_document: ExtractedDocument
    chunks: list[ChunkedText]
    embedded_chunks: list[EmbeddedChunk]
    metadata: PackMetadata
    pack_directory: str
    pack_json_path: str
    chunks_json_path: str
    vectors_npy_path: str
    zip_path: str

