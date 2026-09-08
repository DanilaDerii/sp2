"""Complete summary-context API routes for the student backend."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from student.domain.retrieval.models import SummaryContextChunk, SummaryContextPacket
from student.domain.retrieval.summary_context_builder import (
    SummaryContextError,
    SummaryContextNotFoundError,
    build_file_summary_context,
    build_pack_summary_context,
)


router = APIRouter(prefix="/summaries", tags=["summaries"])


class FileSummaryContextRequest(BaseModel):
    """Request complete context for one source file."""

    installed_pack_id: int = Field(..., gt=0)
    source_id: str = Field(..., min_length=1)


class PackSummaryContextRequest(BaseModel):
    """Request complete context for one installed pack."""

    installed_pack_id: int = Field(..., gt=0)


class SummaryContextChunkResponse(BaseModel):
    """One complete stored chunk returned for summarization."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None


class SummaryContextResponse(BaseModel):
    """Complete ordered context returned for an LM Studio summary."""

    mode: Literal["file_summary_context", "pack_summary_context"]
    installed_pack_id: int
    pack_id: str
    pack_title: str
    source_id: str | None
    source_count: int
    chunk_count: int
    chunks: list[SummaryContextChunkResponse]
    message: str


def _summary_chunk_response(
    chunk: SummaryContextChunk,
) -> SummaryContextChunkResponse:
    return SummaryContextChunkResponse(
        chunk_id=chunk.chunk_id,
        source_id=chunk.source_id,
        source_type=chunk.source_type,
        source_title=chunk.source_title,
        text=chunk.text,
        chunk_index=chunk.chunk_index,
        page=chunk.page,
        section=chunk.section,
    )


def _summary_context_response(
    packet: SummaryContextPacket,
) -> SummaryContextResponse:
    return SummaryContextResponse(
        mode=packet.mode,
        installed_pack_id=packet.installed_pack_id,
        pack_id=packet.pack_id,
        pack_title=packet.pack_title,
        source_id=packet.source_id,
        source_count=packet.source_count,
        chunk_count=packet.chunk_count,
        chunks=[_summary_chunk_response(chunk) for chunk in packet.chunks],
        message=packet.message,
    )


def _summary_context_http_error(exc: SummaryContextError) -> HTTPException:
    if isinstance(exc, SummaryContextNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    )


@router.post("/file-context", response_model=SummaryContextResponse)
def get_file_summary_context(
    request: FileSummaryContextRequest,
) -> SummaryContextResponse:
    """Return every ordered chunk for one source file."""
    try:
        packet = build_file_summary_context(
            installed_pack_id=request.installed_pack_id,
            source_id=request.source_id,
        )
    except SummaryContextError as exc:
        raise _summary_context_http_error(exc) from exc
    return _summary_context_response(packet)


@router.post("/pack-context", response_model=SummaryContextResponse)
def get_pack_summary_context(
    request: PackSummaryContextRequest,
) -> SummaryContextResponse:
    """Return every ordered chunk from every source in one installed pack."""
    try:
        packet = build_pack_summary_context(
            installed_pack_id=request.installed_pack_id,
        )
    except SummaryContextError as exc:
        raise _summary_context_http_error(exc) from exc
    return _summary_context_response(packet)
