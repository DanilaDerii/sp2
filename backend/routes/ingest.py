"""Teacher ingest API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from teacher.domain.orchestrators.bundle_parsing import build_pack_from_path
from teacher.domain.rag.common.embedder import EmbeddingRequestError
from teacher.domain.rag.common.models import TeacherPipelineResult


router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestFilePathRequest(BaseModel):
    """Request body for building a teacher pack from a local source path."""

    file_path: str = Field(..., min_length=1)


class TeacherIngestResponse(BaseModel):
    """Summary returned after building a teacher pack."""

    source_path: str
    pack_id: str
    title: str
    page_count: int
    chunk_count: int
    embedding_model: str
    embedding_dim: int
    zip_path: str


def _teacher_ingest_response(result: TeacherPipelineResult) -> TeacherIngestResponse:
    return TeacherIngestResponse(
        source_path=result.source_path,
        pack_id=result.metadata.pack_id,
        title=result.metadata.title,
        page_count=result.page_count,
        chunk_count=result.chunk_count,
        embedding_model=result.metadata.embedding_model,
        embedding_dim=result.metadata.embedding_dim,
        zip_path=result.zip_path,
    )


@router.post(
    "/file-path",
    response_model=TeacherIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_file_path(request: IngestFilePathRequest) -> TeacherIngestResponse:
    """Build a teacher pack from a local supported source path."""
    try:
        result = build_pack_from_path(request.file_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmbeddingRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return _teacher_ingest_response(result)
