"""Helpers for teacher-side generated pack artifacts."""

import shutil
from pathlib import Path

from ..rag.common.models import TeacherArtifactPaths


REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"


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


def teacher_artifact_paths(
    pack_id: str,
    *,
    artifacts_dir: str | Path = ARTIFACTS_DIR,
) -> TeacherArtifactPaths:
    """Build standard root-artifact paths for one teacher pack."""
    safe_name = _safe_artifact_name(pack_id)
    artifact_root = Path(artifacts_dir).expanduser().resolve()

    return TeacherArtifactPaths(
        pack_id=pack_id,
        pack_dir=artifact_root / f"{safe_name}_pack",
        zip_path=artifact_root / f"{safe_name}.zip",
    )


def prepare_teacher_artifacts(
    pack_id: str,
    *,
    artifacts_dir: str | Path = ARTIFACTS_DIR,
    rewrite_existing: bool = True,
) -> TeacherArtifactPaths:
    """Create clean output locations for one teacher pipeline run."""
    paths = teacher_artifact_paths(pack_id, artifacts_dir=artifacts_dir)
    paths.pack_dir.parent.mkdir(parents=True, exist_ok=True)

    if paths.pack_dir.exists():
        if not rewrite_existing:
            raise FileExistsError(f"Pack artifact directory already exists: {paths.pack_dir}")
        if not paths.pack_dir.is_dir():
            raise ValueError(f"Expected pack artifact directory, got file: {paths.pack_dir}")
        shutil.rmtree(paths.pack_dir)

    if paths.zip_path.exists():
        if not rewrite_existing:
            raise FileExistsError(f"Pack artifact zip already exists: {paths.zip_path}")
        if not paths.zip_path.is_file():
            raise ValueError(f"Expected pack artifact zip, got directory: {paths.zip_path}")
        paths.zip_path.unlink()

    paths.pack_dir.mkdir(parents=True, exist_ok=True)
    return paths
