"""Uninstall one installed pack from every student storage backend."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from storage.cruds.lancedb.chunk_repository import delete_chunks_for_installed_pack
from storage.cruds.sqlite.pack_repository import (
    InstalledPack,
    delete_installed_pack,
    get_installed_pack,
)


STORAGE_DIR = Path(__file__).resolve().parents[1]
INSTALLED_PACKS_DIR = STORAGE_DIR / "installed_packs"


class PackUninstallError(RuntimeError):
    """Raised when an installed pack cannot be fully uninstalled."""


class InstalledPackNotFoundError(PackUninstallError):
    """Raised when the requested installed pack does not exist."""


@dataclass(frozen=True, slots=True)
class PackUninstallResult:
    """Summary of one installed-pack uninstall operation."""

    installed_pack: InstalledPack
    deleted_chunk_count: int
    deleted_files: bool
    deleted_sqlite_row: bool


def _resolve_installed_pack_path(install_path: str | Path) -> Path:
    root = INSTALLED_PACKS_DIR.resolve()
    target = Path(install_path).expanduser().resolve()

    if target == root:
        raise PackUninstallError("Refusing to delete the installed_packs root directory")
    if not target.is_relative_to(root):
        raise PackUninstallError(
            f"Installed pack path is outside the installed_packs directory: {target}"
        )
    return target


def _delete_installed_pack_files(install_path: str | Path) -> bool:
    target = _resolve_installed_pack_path(install_path)
    if not target.exists():
        return False
    if not target.is_dir():
        raise PackUninstallError(f"Expected installed pack directory, got file: {target}")

    shutil.rmtree(target)
    return True


def uninstall_pack(installed_pack_id: int) -> PackUninstallResult:
    """Uninstall one pack from LanceDB, the filesystem, and SQLite."""
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise InstalledPackNotFoundError(f"Installed pack not found: {installed_pack_id}")

    deleted_chunk_count = delete_chunks_for_installed_pack(installed_pack.id)
    deleted_files = _delete_installed_pack_files(installed_pack.install_path)
    deleted_sqlite_row = delete_installed_pack(installed_pack.id)
    if not deleted_sqlite_row:
        raise PackUninstallError(
            f"Installed pack row disappeared before uninstall completed: {installed_pack.id}"
        )

    return PackUninstallResult(
        installed_pack=installed_pack,
        deleted_chunk_count=deleted_chunk_count,
        deleted_files=deleted_files,
        deleted_sqlite_row=deleted_sqlite_row,
    )
