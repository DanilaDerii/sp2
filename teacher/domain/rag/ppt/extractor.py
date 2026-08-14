"""Slide-aware PPT and PPTX text extraction worker."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from ..common.models import ExtractedDocument, ExtractedPage


_LIBREOFFICE_PLACEHOLDER_TEXT = {
    "<date/time>",
    "<footer>",
    "<header>",
    "<number>",
}


def _normalized_text(value: str) -> str:
    text = " ".join(value.split()).strip()
    if text.casefold() in _LIBREOFFICE_PLACEHOLDER_TEXT:
        return ""
    return text


def _shape_position(shape: Any) -> tuple[int, int]:
    return int(getattr(shape, "top", 0)), int(getattr(shape, "left", 0))


def _pptx_shape_text_blocks(shape: Any) -> list[str]:
    blocks: list[str] = []

    if getattr(shape, "has_text_frame", False):
        text = _normalized_text(shape.text)
        if text:
            blocks.append(text)

    if getattr(shape, "has_table", False):
        for row in shape.table.rows:
            row_text = " | ".join(
                text
                for cell in row.cells
                if (text := _normalized_text(cell.text))
            )
            if row_text:
                blocks.append(row_text)

    child_shapes = getattr(shape, "shapes", None)
    if child_shapes is not None:
        for child in sorted(child_shapes, key=_shape_position):
            blocks.extend(_pptx_shape_text_blocks(child))

    return blocks


def _extract_pptx_pages(source_path: Path) -> list[ExtractedPage]:
    try:
        from pptx import Presentation
    except ImportError as exc:
        raise RuntimeError(
            "PPTX extraction requires python-pptx from environment/requirements.txt"
        ) from exc

    try:
        presentation = Presentation(source_path)
        pages: list[ExtractedPage] = []
        for slide_number, slide in enumerate(presentation.slides, start=1):
            blocks: list[str] = []
            for shape in sorted(slide.shapes, key=_shape_position):
                blocks.extend(_pptx_shape_text_blocks(shape))
            pages.append(
                ExtractedPage(
                    page_number=slide_number,
                    text="\n".join(blocks),
                )
            )
        return pages
    except Exception as exc:
        raise RuntimeError(
            f"python-pptx failed to extract text from {source_path.name}: {exc}"
        ) from exc


def _extract_legacy_ppt_pages(source_path: Path) -> list[ExtractedPage]:
    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
    if libreoffice is None:
        raise RuntimeError(
            "Legacy PPT extraction requires LibreOffice on the system PATH"
        )

    with TemporaryDirectory(prefix="sp2-legacy-ppt-") as temporary_dir:
        temporary_root = Path(temporary_dir)
        output_dir = temporary_root / "output"
        profile_dir = temporary_root / "libreoffice-profile"
        output_dir.mkdir()
        profile_dir.mkdir()

        try:
            completed = subprocess.run(
                [
                    libreoffice,
                    f"-env:UserInstallation={profile_dir.as_uri()}",
                    "--headless",
                    "--convert-to",
                    "pptx",
                    "--outdir",
                    str(output_dir),
                    str(source_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"LibreOffice timed out while reading {source_path.name}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Could not run LibreOffice for {source_path.name}: {exc}"
            ) from exc

        converted_path = output_dir / f"{source_path.stem}.pptx"
        if completed.returncode != 0 or not converted_path.is_file():
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"LibreOffice failed to read {source_path.name}: "
                f"{detail or 'no PPTX output was created'}"
            )

        return _extract_pptx_pages(converted_path)


def extract_powerpoint_text(presentation_path: str | Path) -> ExtractedDocument:
    """Extract text from a PowerPoint presentation while preserving slide numbers."""
    source_path = Path(presentation_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"PowerPoint presentation not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")

    suffix = source_path.suffix.lower()
    if suffix not in {".ppt", ".pptx"}:
        raise ValueError(f"Expected a PPT or PPTX file, got: {source_path.name}")

    pages = (
        _extract_pptx_pages(source_path)
        if suffix == ".pptx"
        else _extract_legacy_ppt_pages(source_path)
    )
    if not pages or not any(page.text for page in pages):
        raise RuntimeError(
            f"PowerPoint extraction produced no text from {source_path.name}"
        )

    return ExtractedDocument(
        source_path=str(source_path),
        page_count=len(pages),
        pages=pages,
    )
