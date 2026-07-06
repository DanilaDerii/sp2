"""Delete one installed pack across student storage backends."""

from __future__ import annotations

from dataclasses import dataclass

from storage.cruds.installed_pack_manager.manager import (
    InstalledPackFileError,
    delete_installed_pack_files,
)
from storage.cruds.lancedb.chunk_repository import delete_chunks_for_installed_pack
from storage.cruds.sqlite.pack_repository import (
    InstalledPack,
    delete_installed_pack,
    get_installed_pack,
)


class InstalledPackCleanError(RuntimeError):
    """Raised when an installed pack cleanup cannot be completed."""


class InstalledPackNotFoundError(InstalledPackCleanError):
    """Raised when the requested installed pack row does not exist."""


@dataclass(frozen=True, slots=True)
class InstalledPackCleanResult:
    """Summary of one installed pack cleanup."""

    installed_pack: InstalledPack
    deleted_chunk_count: int
    deleted_files: bool
    deleted_sqlite_row: bool


def delete_installed_pack_everywhere(installed_pack_id: int) -> InstalledPackCleanResult:
    """Delete one installed pack from LanceDB, installed files, and SQLite."""
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise InstalledPackNotFoundError(f"Installed pack not found: {installed_pack_id}")

    deleted_chunk_count = delete_chunks_for_installed_pack(installed_pack.id)

    try:
        deleted_files = delete_installed_pack_files(installed_pack.install_path)
    except InstalledPackFileError as exc:
        raise InstalledPackCleanError(str(exc)) from exc

    deleted_sqlite_row = delete_installed_pack(installed_pack.id)
    if not deleted_sqlite_row:
        raise InstalledPackCleanError(
            f"Installed pack row disappeared before cleanup completed: {installed_pack.id}"
        )

    return InstalledPackCleanResult(
        installed_pack=installed_pack,
        deleted_chunk_count=deleted_chunk_count,
        deleted_files=deleted_files,
        deleted_sqlite_row=deleted_sqlite_row,
    )
