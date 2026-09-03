"""Clear installed packs and recreate the student databases."""

from __future__ import annotations

import shutil
from pathlib import Path

from storage.database.setup.create_lancedb_db import LANCE_DIR, create_lancedb_db
from storage.database.setup.create_sqlite_db import SQLITE_DB_PATH, create_sqlite_db


STORAGE_DIR = Path(__file__).resolve().parents[2]
INSTALLED_PACKS_DIR = STORAGE_DIR / "installed_packs"
SQLITE_SIDE_FILES = (
    Path(f"{SQLITE_DB_PATH}-shm"),
    Path(f"{SQLITE_DB_PATH}-wal"),
)


def _installed_pack_paths() -> list[Path]:
    if not INSTALLED_PACKS_DIR.exists():
        return []
    return sorted(
        (
            path
            for path in INSTALLED_PACKS_DIR.iterdir()
            if path.name != ".gitkeep"
        ),
        key=lambda path: path.name.casefold(),
    )


def _clear_installed_packs(*, dry_run: bool) -> None:
    installed_pack_paths = _installed_pack_paths()
    if dry_run:
        if not installed_pack_paths:
            print(f"No installed pack files to delete from: {INSTALLED_PACKS_DIR}")
        for path in installed_pack_paths:
            print(f"Would delete installed pack path: {path}")
        return

    for path in installed_pack_paths:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            raise RuntimeError(f"Unsupported installed pack path type: {path}")
        print(f"Deleted installed pack path: {path}")


def _reset_sqlite(*, dry_run: bool) -> None:
    paths = (SQLITE_DB_PATH, *SQLITE_SIDE_FILES)
    for path in paths:
        if dry_run:
            print(f"Would delete SQLite file if present: {path}")
        elif path.exists():
            path.unlink()
            print(f"Deleted SQLite file: {path}")

    if dry_run:
        print(f"Would recreate SQLite database: {SQLITE_DB_PATH}")
    else:
        create_sqlite_db()


def _reset_lancedb(*, dry_run: bool) -> None:
    if dry_run:
        print(f"Would delete LanceDB directory if present: {LANCE_DIR}")
        print("Would recreate LanceDB schema with the project vector dimension")
        return

    if LANCE_DIR.exists():
        shutil.rmtree(LANCE_DIR)
        print(f"Deleted LanceDB directory: {LANCE_DIR}")

    create_lancedb_db()


def clear_out_student_storage(*, dry_run: bool = True) -> None:
    """Clear installed packs and recreate SQLite and LanceDB together."""
    _clear_installed_packs(dry_run=dry_run)
    _reset_sqlite(dry_run=dry_run)
    _reset_lancedb(dry_run=dry_run)
