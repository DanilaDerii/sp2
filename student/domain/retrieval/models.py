"""Internal retrieval-layer data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ContextMode = Literal["course_context", "no_course_context"]
SummaryContextMode = Literal["file_summary_context", "pack_summary_context"]


@dataclass(frozen=True, slots=True)
class QueryEmbedding:
    """One embedded student question."""

    vector: list[float]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One LanceDB search hit shaped for context building."""

    chunk_id: str
    installed_pack_id: int
    pack_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None
    distance: float | None
    score: float | None


@dataclass(frozen=True, slots=True)
class CourseContextPacket:
    """Structured context returned to the future LM Studio tool layer."""

    mode: ContextMode
    installed_pack_id: int
    pack_id: str
    embedding_model: str
    chunks: list[RetrievedChunk]
    message: str


@dataclass(frozen=True, slots=True)
class SummaryContextChunk:
    """One complete stored chunk returned for LLM summarization."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None


@dataclass(frozen=True, slots=True)
class SummaryContextPacket:
    """Complete ordered source context for an LM Studio summary."""

    mode: SummaryContextMode
    installed_pack_id: int
    pack_id: str
    pack_title: str
    source_id: str | None
    source_count: int
    chunk_count: int
    chunks: list[SummaryContextChunk]
    message: str
