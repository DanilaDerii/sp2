"""Import portable teacher pack zips into student storage."""

from __future__ import annotations

import argparse
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile, is_zipfile

from student.storage.database.setup.create_sqlite_db import create_sqlite_db
from student.storage.cruds.lancedb.chunk_repository import (
    PackChunk,
    add_pack_chunks,
    count_chunks_for_installed_pack,
    delete_chunks_for_installed_pack,
)
from student.storage.cruds.sqlite.pack_repository import (
    InstalledPack,
    create_installed_pack,
    delete_installed_pack,
)

from .pack_validator import REQUIRED_PACK_FILES, PackValidationError, validate_pack_directory


STORAGE_DIR = Path(__file__).resolve().parents[1]
INSTALLED_PACKS_DIR = STORAGE_DIR / "installed_packs"


class PackImportError(RuntimeError):
    """Raised when a pack zip cannot be imported into student storage."""


@dataclass(frozen=True, slots=True)
class ImportedPack:
    """Summary of a successfully imported teacher pack."""

    installed_pack: InstalledPack
    chunk_count: int
    install_path: str


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
                topic=chunk.topic,
                char_count=chunk.char_count,
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

        final_install_dir = root / _safe_name(f"{metadata.pack_id}-{metadata.version}")
        if final_install_dir.exists():
            raise PackImportError(
                "Pack install directory already exists. "
                f"Duplicate/update handling is not implemented yet: {final_install_dir}"
            )

        temp_dir.rename(final_install_dir)
        validated_pack = validate_pack_directory(final_install_dir)
        metadata = validated_pack.metadata

        create_sqlite_db()
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
        )

        pack_chunks = _pack_chunks_from_validated_pack(validated_pack, installed_pack.id)
        inserted_count = add_pack_chunks(pack_chunks)
        if inserted_count != len(pack_chunks):
            raise PackImportError(
                f"Inserted {inserted_count} LanceDB rows for {len(pack_chunks)} chunks"
            )

        return ImportedPack(
            installed_pack=installed_pack,
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


if __name__ == "__main__":
    main()
