"""App settings API routes for the student backend."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from config.arguments import DEFAULT_PACK_SOURCE_DIR_SETTING_KEY
from storage.cruds.sqlite.settings_repository import get_setting, set_setting


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class DefaultPackSourceDirResponse(BaseModel):
    """Currently configured default pack source directory, if any."""

    path: str | None


class SetDefaultPackSourceDirRequest(BaseModel):
    """Request body for setting the default pack source directory."""

    path: str = Field(..., min_length=1)


@router.get("/default-pack-source-dir", response_model=DefaultPackSourceDirResponse)
def get_default_pack_source_dir() -> DefaultPackSourceDirResponse:
    """Return the configured default pack source directory, if any."""
    return DefaultPackSourceDirResponse(
        path=get_setting(DEFAULT_PACK_SOURCE_DIR_SETTING_KEY)
    )


@router.post("/default-pack-source-dir", response_model=DefaultPackSourceDirResponse)
def set_default_pack_source_dir(
    request: SetDefaultPackSourceDirRequest,
) -> DefaultPackSourceDirResponse:
    """Set the directory sp2_import_pack_by_name scans for course packs."""
    resolved_dir = Path(request.path).expanduser().resolve()
    if not resolved_dir.is_dir():
        logger.warning("Rejected default pack source dir (not a directory): %s", resolved_dir)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a directory: {resolved_dir}",
        )

    set_setting(DEFAULT_PACK_SOURCE_DIR_SETTING_KEY, str(resolved_dir))
    return DefaultPackSourceDirResponse(path=str(resolved_dir))
