"""Helpers for teacher-side generated pack artifacts."""

from pathlib import Path
from config.arguments import ARTIFACTS_DIR


def _safe_artifact_name(pack_id: str) -> str:
    """Return a filesystem-safe artifact stem derived from a pack id."""
    normalized = pack_id.strip()
    if not normalized:
        raise ValueError("pack_id must not be empty")

    safe_chars = []
    for char in normalized:
        if char.isalnum() or char in {"-", "_"}:
            safe_chars.append(char)
        elif char.isspace():
            safe_chars.append("-")
        else:
            raise ValueError(
                "pack_id may only contain letters, numbers, spaces, hyphens, "
                f"and underscores: {pack_id!r}"
            )

    safe_name = "".join(safe_chars).strip("-_")
    if not safe_name:
        raise ValueError("pack_id must contain at least one valid name character")
    return safe_name


def teacher_artifact_zip_path(
    pack_id: str,
    *,
    artifacts_dir: str | Path = ARTIFACTS_DIR,
) -> Path:
    """Return the final zip path for one teacher pack."""
    safe_name = _safe_artifact_name(pack_id)
    artifact_root = Path(artifacts_dir).expanduser().resolve()
    return artifact_root / f"{safe_name}.zip"


def prepare_zip_destination(
    zip_path: str | Path,
    *,
    rewrite_existing: bool = True,
) -> Path:
    """Validate and return a final zip destination without deleting existing output."""
    destination = Path(zip_path).expanduser().resolve()
    if destination.suffix.lower() != ".zip":
        raise ValueError(f"Teacher pack artifact must use the .zip extension: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file():
            raise ValueError(f"Expected pack artifact zip, got directory: {destination}")
        if not rewrite_existing:
            raise FileExistsError(f"Pack artifact zip already exists: {destination}")

    return destination
