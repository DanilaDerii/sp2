"""Pack management API routes for the student backend."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from storage.cruds.installed_pack_cleaner import (
    InstalledPackCleanError,
    InstalledPackCleanResult,
    InstalledPackNotFoundError,
    delete_installed_pack_everywhere,
)
from storage.cruds.sqlite.pack_repository import (
    InstalledPack,
    get_installed_pack,
    list_installed_packs,
)
from storage.importer.pack_importer import ImportedPack, PackImportError, import_pack_zip
from storage.importer.pack_validator import PackValidationError


router = APIRouter(prefix="/packs", tags=["packs"])


class InstalledPackResponse(BaseModel):
    """Installed pack record exposed by the API."""

    id: int
    pack_id: str
    title: str
    version: str
    description: str | None
    embedding_model: str
    embedding_dim: int
    default_top_k: int
    builder_version: str | None
    pack_created_at: str
    install_path: str
    installed_at: str
    is_active: bool


class ImportPackPathRequest(BaseModel):
    """Request body for importing a local teacher pack zip by path."""

    pack_zip_path: str = Field(..., min_length=1)


class ImportedPackResponse(BaseModel):
    """Summary returned after importing a teacher pack."""

    installed_pack: InstalledPackResponse
    chunk_count: int
    install_path: str


class DeletedInstalledPackResponse(BaseModel):
    """Summary returned after deleting one installed pack."""

    installed_pack: InstalledPackResponse
    deleted_chunk_count: int
    deleted_files: bool
    deleted_sqlite_row: bool


def _installed_pack_response(installed_pack: InstalledPack) -> InstalledPackResponse:
    return InstalledPackResponse(
        id=installed_pack.id,
        pack_id=installed_pack.pack_id,
        title=installed_pack.title,
        version=installed_pack.version,
        description=installed_pack.description,
        embedding_model=installed_pack.embedding_model,
        embedding_dim=installed_pack.embedding_dim,
        default_top_k=installed_pack.default_top_k,
        builder_version=installed_pack.builder_version,
        pack_created_at=installed_pack.pack_created_at,
        install_path=installed_pack.install_path,
        installed_at=installed_pack.installed_at,
        is_active=installed_pack.is_active,
    )


def _imported_pack_response(imported_pack: ImportedPack) -> ImportedPackResponse:
    return ImportedPackResponse(
        installed_pack=_installed_pack_response(imported_pack.installed_pack),
        chunk_count=imported_pack.chunk_count,
        install_path=imported_pack.install_path,
    )


def _deleted_installed_pack_response(
    cleaned_pack: InstalledPackCleanResult,
) -> DeletedInstalledPackResponse:
    return DeletedInstalledPackResponse(
        installed_pack=_installed_pack_response(cleaned_pack.installed_pack),
        deleted_chunk_count=cleaned_pack.deleted_chunk_count,
        deleted_files=cleaned_pack.deleted_files,
        deleted_sqlite_row=cleaned_pack.deleted_sqlite_row,
    )


@router.get("", response_model=list[InstalledPackResponse])
def list_packs(
    pack_id: str | None = None,
    active_only: bool = False,
) -> list[InstalledPackResponse]:
    """List installed student packs."""
    return [
        _installed_pack_response(installed_pack)
        for installed_pack in list_installed_packs(
            pack_id=pack_id,
            active_only=active_only,
        )
    ]


@router.get("/{installed_pack_id}", response_model=InstalledPackResponse)
def get_pack(installed_pack_id: int) -> InstalledPackResponse:
    """Return one installed pack by local id."""
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Installed pack not found: {installed_pack_id}",
        )
    return _installed_pack_response(installed_pack)


@router.post(
    "/import-path",
    response_model=ImportedPackResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_pack_from_path(request: ImportPackPathRequest) -> ImportedPackResponse:
    """Import a local teacher-exported .zip pack by filesystem path."""
    try:
        imported_pack = import_pack_zip(request.pack_zip_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (PackImportError, PackValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _imported_pack_response(imported_pack)


@router.delete("/{installed_pack_id}", response_model=DeletedInstalledPackResponse)
def delete_pack(installed_pack_id: int) -> DeletedInstalledPackResponse:
    """Delete one installed pack from student storage."""
    try:
        cleaned_pack = delete_installed_pack_everywhere(installed_pack_id)
    except InstalledPackNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InstalledPackCleanError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return _deleted_installed_pack_response(cleaned_pack)
