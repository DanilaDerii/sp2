"""Course source installation API route."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.course_installer import install_course_source
from storage.importer.pack_importer import PackImportError
from storage.importer.pack_validator import PackValidationError
from teacher.domain.rag.common.embedder import EmbeddingRequestError


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


class InstallSourceRequest(BaseModel):
    """Request body for installing one local course source."""

    source_path: str = Field(..., min_length=1)


class InstalledSourceResponse(BaseModel):
    """Small response used by the MCP install tool."""

    source_path: str
    source_kind: str
    zip_path: str
    installed_pack_id: int
    pack_id: str
    title: str
    chunk_count: int
    install_path: str
    embedding_model: str
    embedding_dim: int
    replaced_installed_pack_ids: list[int]


@router.post(
    "/source",
    response_model=InstalledSourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def install_source(request: InstallSourceRequest) -> InstalledSourceResponse:
    """Install a raw course file, a source directory, or an SP2 pack ZIP."""
    try:
        result = install_course_source(request.source_path)
    except FileNotFoundError as exc:
        logger.warning("Course source not found at %s: %s", request.source_path, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (PackImportError, PackValidationError, ValueError) as exc:
        logger.warning("Course source rejected for %s: %s", request.source_path, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except EmbeddingRequestError as exc:
        logger.error("Embedding request failed for %s: %s", request.source_path, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.exception("Unexpected install failure for %s", request.source_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    imported = result.imported_pack
    installed = imported.installed_pack
    return InstalledSourceResponse(
        source_path=result.source_path,
        source_kind=result.source_kind,
        zip_path=result.zip_path,
        installed_pack_id=installed.id,
        pack_id=installed.pack_id,
        title=installed.title,
        chunk_count=imported.chunk_count,
        install_path=imported.install_path,
        embedding_model=installed.embedding_model,
        embedding_dim=installed.embedding_dim,
        replaced_installed_pack_ids=imported.replaced_installed_pack_ids,
    )
