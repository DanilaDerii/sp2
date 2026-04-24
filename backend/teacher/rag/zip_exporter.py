"""Zip export worker for portable teacher-side pack output."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")


def export_pack_zip(
    pack_dir: str | Path,
    output_zip_path: str | Path,
) -> str:
    """Zip a written pack directory into the portable v1 export artifact."""
    pack_path = Path(pack_dir).expanduser().resolve()
    zip_path = Path(output_zip_path).expanduser().resolve()

    if not pack_path.exists():
        raise FileNotFoundError(f"Pack directory not found: {pack_path}")
    if not pack_path.is_dir():
        raise ValueError(f"Expected a directory, got: {pack_path}")

    missing_files = [
        file_name for file_name in REQUIRED_PACK_FILES if not (pack_path / file_name).exists()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Pack directory is missing required files: " + ", ".join(missing_files)
        )

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_name in REQUIRED_PACK_FILES:
            zip_file.write(pack_path / file_name, arcname=file_name)

    return str(zip_path)
