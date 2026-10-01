"""Install either raw course material or an exported SP2 pack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from storage.importer.pack_importer import ImportedPack, import_pack_zip
from teacher.domain.orchestrators.bundle_parsing import build_pack_from_path


@dataclass(frozen=True, slots=True)
class CourseInstallResult:
    """Result of building or importing one course source."""

    source_path: str
    source_kind: str
    zip_path: str
    imported_pack: ImportedPack


def install_course_source(source_path: str | Path) -> CourseInstallResult:
    """Install a raw file, a source directory, or an exported pack ZIP."""
    resolved_source = Path(source_path).expanduser().resolve()
    if not resolved_source.exists():
        raise FileNotFoundError(f"Course source not found: {resolved_source}")

    if resolved_source.is_file() and resolved_source.suffix.casefold() == ".zip":
        zip_path = resolved_source
        source_kind = "pack_zip"
    else:
        teacher_result = build_pack_from_path(resolved_source)
        zip_path = Path(teacher_result.zip_path).expanduser().resolve()
        source_kind = "course_material"

    return CourseInstallResult(
        source_path=str(resolved_source),
        source_kind=source_kind,
        zip_path=str(zip_path),
        imported_pack=import_pack_zip(zip_path),
    )
