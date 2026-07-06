"""Filesystem manager for installed student pack directories."""

from __future__ import annotations

import shutil
from pathlib import Path


STORAGE_DIR = Path(__file__).resolve().parents[2]
INSTALLED_PACKS_DIR = STORAGE_DIR / "installed_packs"


class InstalledPackFileError(RuntimeError):
    """Raised when installed pack files cannot be safely managed."""


def _resolve_installed_pack_path(install_path: str | Path) -> Path:
    root = INSTALLED_PACKS_DIR.resolve()
    target = Path(install_path).expanduser().resolve()

    if target == root:
        raise InstalledPackFileError("Refusing to delete the installed_packs root directory")
    if not target.is_relative_to(root):
        raise InstalledPackFileError(
            f"Installed pack path is outside the installed_packs directory: {target}"
        )
    return target


def delete_installed_pack_files(install_path: str | Path) -> bool:
    """Delete one installed pack directory and return whether files were removed."""
    target = _resolve_installed_pack_path(install_path)
    if not target.exists():
        return False
    if not target.is_dir():
        raise InstalledPackFileError(f"Expected installed pack directory, got file: {target}")

    shutil.rmtree(target)
    return True
