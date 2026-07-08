"""Teacher ingest API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from teacher.domain.rag.common.embedder import EmbeddingRequestError
from teacher.domain.services import TeacherIngestResult, ingest_path_to_file


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
    pack_dir: str
    zip_path: str


def _teacher_ingest_response(result: TeacherIngestResult) -> TeacherIngestResponse:
    return TeacherIngestResponse(
        source_path=result.source_path,
        pack_id=result.pack_id,
        title=result.title,
        page_count=result.page_count,
        chunk_count=result.chunk_count,
        embedding_model=result.embedding_model,
        embedding_dim=result.embedding_dim,
        pack_dir=result.pack_dir,
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
        result = ingest_path_to_file(request.file_path)
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
