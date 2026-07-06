"""Retrieval context API routes for the student backend."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from student.domain.retrieval.chunk_search import ChunkSearchError
from student.domain.retrieval.context_builder import (
    ContextBuilderError,
    build_course_context_packet,
)
from student.domain.retrieval.embedding_model import EmbeddingModelError
from student.domain.retrieval.models import CourseContextPacket, RetrievedChunk
from student.domain.retrieval.query_embedder import QueryEmbeddingError


router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class CourseContextRequest(BaseModel):
    """Request body for retrieving course context for one question."""

    installed_pack_id: int = Field(..., gt=0)
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, gt=0)
    max_distance: float | None = Field(default=None, ge=0)


class RetrievedChunkResponse(BaseModel):
    """Retrieved course chunk returned to LM Studio tooling."""

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
    topic: str | None
    char_count: int
    distance: float | None
    score: float | None


class CourseContextResponse(BaseModel):
    """Structured retrieval context packet returned by the student API."""

    mode: Literal["course_context", "no_course_context"]
    installed_pack_id: int
    pack_id: str
    question: str
    embedding_model: str
    chunks: list[RetrievedChunkResponse]
    message: str


def _retrieved_chunk_response(chunk: RetrievedChunk) -> RetrievedChunkResponse:
    return RetrievedChunkResponse(
        chunk_id=chunk.chunk_id,
        installed_pack_id=chunk.installed_pack_id,
        pack_id=chunk.pack_id,
        source_id=chunk.source_id,
        source_type=chunk.source_type,
        source_title=chunk.source_title,
        text=chunk.text,
        chunk_index=chunk.chunk_index,
        page=chunk.page,
        section=chunk.section,
        topic=chunk.topic,
        char_count=chunk.char_count,
        distance=chunk.distance,
        score=chunk.score,
    )


def _course_context_response(packet: CourseContextPacket) -> CourseContextResponse:
    return CourseContextResponse(
        mode=packet.mode,
        installed_pack_id=packet.installed_pack_id,
        pack_id=packet.pack_id,
        question=packet.question,
        embedding_model=packet.embedding_model,
        chunks=[_retrieved_chunk_response(chunk) for chunk in packet.chunks],
        message=packet.message,
    )


@router.post("/context", response_model=CourseContextResponse)
def get_course_context(request: CourseContextRequest) -> CourseContextResponse:
    """Return course context or no-context state for a student question."""
    try:
        packet = build_course_context_packet(
            installed_pack_id=request.installed_pack_id,
            question=request.question,
            top_k=request.top_k,
            max_distance=request.max_distance,
        )
    except ContextBuilderError as exc:
        status_code = status.HTTP_404_NOT_FOUND
        if "not active" in str(exc):
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except (EmbeddingModelError, ChunkSearchError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except QueryEmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return _course_context_response(packet)
