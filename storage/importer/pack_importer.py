"""Import portable teacher pack zips into student storage."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile, is_zipfile

from config.arguments import REQUIRED_PACK_FILES
from storage.database.setup.create_sqlite_db import create_sqlite_db
from storage.cruds.lancedb.chunk_repository import (
    PackChunk,
    add_pack_chunks,
    count_chunks_for_installed_pack,
    delete_chunks_for_installed_pack,
)
from storage.cruds.sqlite.pack_repository import (
    InstalledPack,
    create_installed_pack,
    delete_installed_pack,
    get_installed_pack,
    list_installed_packs,
)
from storage.installed_pack_manager import uninstall_pack

from .pack_validator import PackValidationError, validate_pack_directory


logger = logging.getLogger(__name__)

STORAGE_DIR = Path(__file__).resolve().parents[1]
INSTALLED_PACKS_DIR = STORAGE_DIR / "installed_packs"


class PackImportError(RuntimeError):
    """Raised when a pack zip cannot be imported into student storage."""


class PackUpdateSourceNotFoundError(PackImportError):
    """Raised when an installed pack has no usable source to update from."""


@dataclass(frozen=True, slots=True)
class ImportedPack:
    """Summary of a successfully imported teacher pack."""

    installed_pack: InstalledPack
    chunk_count: int
    install_path: str
    replaced_installed_pack_ids: list[int]


def _safe_name(value: str) -> str:
    safe_chars: list[str] = []
    for char in value.strip():
        if char.isalnum() or char in {"-", "_"}:
            safe_chars.append(char)
        elif char.isspace():
            safe_chars.append("-")
        else:
            safe_chars.append("-")

    safe_name = "".join(safe_chars).strip("-_")
    if not safe_name:
        raise PackImportError(f"Could not build a safe install directory name from: {value!r}")
    return safe_name


def _assert_required_zip_members(zip_file: ZipFile) -> None:
    file_names = {member.filename for member in zip_file.infolist() if not member.is_dir()}
    required = set(REQUIRED_PACK_FILES)

    missing = sorted(required - file_names)
    if missing:
        raise PackValidationError("Pack zip is missing required files: " + ", ".join(missing))

    unexpected = sorted(file_names - required)
    if unexpected:
        raise PackValidationError(
            "Pack zip contains files outside the v1 contract: " + ", ".join(unexpected)
        )


def _extract_pack_zip(zip_path: Path, destination: Path) -> None:
    try:
        with ZipFile(zip_path) as zip_file:
            _assert_required_zip_members(zip_file)
            destination.mkdir(parents=True, exist_ok=False)
            destination_root = destination.resolve()

            for member in zip_file.infolist():
                if member.is_dir():
                    continue

                target_path = (destination / member.filename).resolve()
                if not target_path.is_relative_to(destination_root):
                    raise PackValidationError(
                        f"Pack zip member would extract outside install directory: {member.filename}"
                    )

                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zip_file.open(member) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
    except BadZipFile as exc:
        raise PackValidationError(f"Invalid zip file: {zip_path}") from exc


def _peek_pack_id(zip_path: Path) -> str | None:
    """Read pack_id out of a zip's pack.json without extracting it.

    Used to find a matching re-export among unrelated zips (other
    courses, stray downloads) sitting in the same folder. Returns None
    for anything that isn't a readable SP2 pack zip.
    """
    try:
        with ZipFile(zip_path) as zip_file:
            with zip_file.open("pack.json") as pack_json_file:
                return json.load(pack_json_file).get("pack_id")
    except (AttributeError, BadZipFile, KeyError, OSError, ValueError):
        return None


def find_latest_matching_zip(source_dir: Path, pack_id: str) -> Path | None:
    """Return the most recently modified zip in source_dir with this pack_id."""
    if not source_dir.is_dir():
        return None

    matches = [
        candidate
        for candidate in source_dir.glob("*.zip")
        if candidate.is_file() and _peek_pack_id(candidate) == pack_id
    ]
    if not matches:
        return None

    return max(matches, key=lambda candidate: candidate.stat().st_mtime)


def _pack_chunks_from_validated_pack(validated_pack, installed_pack_id: int) -> list[PackChunk]:
    metadata = validated_pack.metadata
    chunks: list[PackChunk] = []

    for chunk, vector in zip(validated_pack.chunks, validated_pack.vectors, strict=True):
        chunks.append(
            PackChunk(
                chunk_id=chunk.chunk_id,
                installed_pack_id=installed_pack_id,
                pack_id=metadata.pack_id,
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                source_title=chunk.source_title,
                text=chunk.text,
                vector=vector.tolist(),
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                section=chunk.section,
            )
        )

    return chunks


def import_pack_zip(
    pack_zip_path: str | Path,
    *,
    install_root: str | Path = INSTALLED_PACKS_DIR,
) -> ImportedPack:
    """Import a teacher-exported .zip pack into SQLite and LanceDB."""
    zip_path = Path(pack_zip_path).expanduser().resolve()
    if not zip_path.exists():
        raise FileNotFoundError(f"Pack zip not found: {zip_path}")
    if not zip_path.is_file():
        raise PackImportError(f"Expected a pack zip file, got directory: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise PackImportError(f"Student pack imports must use the .zip extension: {zip_path}")
    if not is_zipfile(zip_path):
        raise PackValidationError(f"File is not a valid zip archive: {zip_path}")

    root = Path(install_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    temp_dir = root / f".tmp-import-{zip_path.stem}-{uuid.uuid4().hex}"
    final_install_dir: Path | None = None
    installed_pack: InstalledPack | None = None

    try:
        _extract_pack_zip(zip_path, temp_dir)
        validated_pack = validate_pack_directory(temp_dir)
        metadata = validated_pack.metadata

        create_sqlite_db()
        previous_installs = list_installed_packs(pack_id=metadata.pack_id)

        final_install_dir = root / _safe_name(f"{metadata.pack_id}-{metadata.version}")
        if final_install_dir.exists():
            colliding_install = next(
                (
                    previous_install
                    for previous_install in previous_installs
                    if Path(previous_install.install_path).resolve() == final_install_dir.resolve()
                ),
                None,
            )
            if colliding_install is None:
                raise PackImportError(f"Pack install directory already exists: {final_install_dir}")
            # Re-importing the same pack_id/version (e.g. a teacher fixing a
            # typo and regenerating): install into a staging directory so the
            # previous install stays intact until the new one fully succeeds.
            final_install_dir = root / _safe_name(
                f"{metadata.pack_id}-{metadata.version}-{uuid.uuid4().hex[:8]}"
            )

        temp_dir.rename(final_install_dir)
        validated_pack = validate_pack_directory(final_install_dir)
        metadata = validated_pack.metadata

        installed_pack = create_installed_pack(
            pack_id=metadata.pack_id,
            title=metadata.title,
            version=metadata.version,
            description=metadata.description,
            embedding_model=metadata.embedding_model,
            embedding_dim=metadata.embedding_dim,
            default_top_k=metadata.default_top_k,
            builder_version=metadata.builder_version,
            pack_created_at=metadata.created_at,
            install_path=str(final_install_dir),
            source_zip_path=str(zip_path),
        )

        pack_chunks = _pack_chunks_from_validated_pack(validated_pack, installed_pack.id)
        inserted_count = add_pack_chunks(pack_chunks)
        if inserted_count != len(pack_chunks):
            raise PackImportError(
                f"Inserted {inserted_count} LanceDB rows for {len(pack_chunks)} chunks"
            )

        # The new pack is fully installed and searchable - only now is it
        # safe to remove whatever this pack_id previously pointed to. A
        # failure here must not roll back the new pack we just committed to,
        # so it's isolated from the outer except block below.
        replaced_installed_pack_ids: list[int] = []
        for previous_install in previous_installs:
            try:
                uninstall_pack(previous_install.id)
            except Exception:
                logger.warning(
                    "Failed to remove superseded pack %s after updating pack_id %s",
                    previous_install.id,
                    metadata.pack_id,
                    exc_info=True,
                )
            else:
                replaced_installed_pack_ids.append(previous_install.id)

        return ImportedPack(
            installed_pack=installed_pack,
            replaced_installed_pack_ids=replaced_installed_pack_ids,
            chunk_count=count_chunks_for_installed_pack(installed_pack.id),
            install_path=str(final_install_dir),
        )
    except Exception:
        if installed_pack is not None:
            delete_chunks_for_installed_pack(installed_pack.id)
            delete_installed_pack(installed_pack.id)
        if final_install_dir is not None and final_install_dir.exists():
            shutil.rmtree(final_install_dir)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise


def update_installed_pack_from_source(installed_pack_id: int) -> ImportedPack:
    """Re-import an installed pack from wherever it was last imported from.

    Looks for the most recently modified zip sharing this pack's pack_id in
    the same directory as its last import, so a student or teacher can say
    "update my pack" without retyping a file path. Every user's export
    folder looks different, so this is learned from their own prior import
    rather than assumed.
    """
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise PackUpdateSourceNotFoundError(f"Installed pack not found: {installed_pack_id}")
    if not installed_pack.source_zip_path:
        raise PackUpdateSourceNotFoundError(
            f"Installed pack {installed_pack_id} has no recorded source path "
            "to update from. Import it once with an explicit pack_zip_path."
        )

    source_dir = Path(installed_pack.source_zip_path).parent
    latest_zip = find_latest_matching_zip(source_dir, installed_pack.pack_id)
    if latest_zip is None:
        raise PackUpdateSourceNotFoundError(
            f"No pack zip for pack_id={installed_pack.pack_id!r} found in "
            f"{source_dir}. Provide an explicit pack_zip_path to update it."
        )

    return import_pack_zip(latest_zip)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import a teacher .zip pack into student storage.")
    parser.add_argument("pack_zip_path", help="Path to the teacher-exported .zip pack.")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    imported_pack = import_pack_zip(args.pack_zip_path)
    print("Student pack import completed")
    print(f"installed_pack_id: {imported_pack.installed_pack.id}")
    print(f"pack_id: {imported_pack.installed_pack.pack_id}")
    print(f"title: {imported_pack.installed_pack.title}")
    print(f"version: {imported_pack.installed_pack.version}")
    print(f"chunks: {imported_pack.chunk_count}")
    print(f"install_path: {imported_pack.install_path}")
    if imported_pack.replaced_installed_pack_ids:
        print(f"replaced_installed_pack_ids: {imported_pack.replaced_installed_pack_ids}")


if __name__ == "__main__":
    main()
