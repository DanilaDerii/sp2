"""Internal helpers for file-or-directory teacher pack builds."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from teacher.domain.orchestrators.pack_writer import write_pack_directory
from teacher.domain.orchestrators.zip_exporter import export_pack_zip
from teacher.domain.rag.common.models import (
    EmbeddedChunk,
    ExtractedDocument,
    PackMetadata,
)
from teacher.domain.rag.doc.docx.extractor import extract_docx_text
from teacher.domain.rag.doc.odt.extractor import extract_odt_text
from teacher.domain.rag.pdf.extractor import extract_pdf_text
from teacher.domain.rag.ppt.extractor import extract_powerpoint_text


_ExtractDocument = Callable[[str | Path], ExtractedDocument]
_SourceExtractor = tuple[str, _ExtractDocument]

_SOURCE_EXTRACTORS: dict[str, _SourceExtractor] = {
    ".pdf": ("pdf", extract_pdf_text),
    ".odt": ("odt", extract_odt_text),
    ".docx": ("docx", extract_docx_text),
    ".ppt": ("ppt", extract_powerpoint_text),
    ".pptx": ("pptx", extract_powerpoint_text),
}


def _resolve_source_path(source_path: str | Path) -> Path:
    """Resolve and validate a selected teacher source path."""
    resolved_source = Path(source_path).expanduser().resolve()
    if not resolved_source.exists():
        raise FileNotFoundError(f"Teacher source path not found: {resolved_source}")
    if not resolved_source.is_file() and not resolved_source.is_dir():
        raise ValueError(f"Teacher source must be a file or directory: {resolved_source}")
    return resolved_source


def _extractor_for_path(source_path: str | Path) -> _SourceExtractor:
    """Return the source type and extractor registered for a source file."""
    resolved_source = Path(source_path).expanduser()
    extractor = _SOURCE_EXTRACTORS.get(resolved_source.suffix.lower())
    if extractor is None:
        supported = ", ".join(_SOURCE_EXTRACTORS)
        raise ValueError(
            f"Unsupported source file type for {resolved_source.name!r}. "
            f"Supported file types: {supported}"
        )
    return extractor


def _discover_supported_files(source_path: Path) -> list[Path]:
    """Return one selected file or recursively discovered directory files."""
    if source_path.is_file():
        _extractor_for_path(source_path)
        return [source_path]

    source_files = [
        path
        for path in source_path.rglob("*")
        if path.is_file() and path.suffix.lower() in _SOURCE_EXTRACTORS
    ]
    return sorted(
        source_files,
        key=lambda path: (
            path.relative_to(source_path).as_posix().casefold(),
            path.relative_to(source_path).as_posix(),
        ),
    )


def _source_id_for_path(selected_path: Path, source_path: Path) -> str:
    """Return a portable source id relative to the selected input path."""
    source_root = selected_path if selected_path.is_dir() else selected_path.parent
    try:
        relative_source = source_path.relative_to(source_root)
    except ValueError as exc:
        raise ValueError(
            f"Teacher source is outside the selected path: {source_path}"
        ) from exc

    source_id = relative_source.as_posix()
    if not source_id or source_id == ".":
        raise ValueError(f"Could not derive a relative source id: {source_path}")
    return source_id


def _default_pack_id(source_path: Path) -> str:
    """Derive a simple pack id from the selected file or directory name."""
    source_name = source_path.stem if source_path.is_file() else source_path.name
    safe_chars: list[str] = []
    previous_was_separator = False

    for char in source_name.strip().lower():
        if char.isalnum() or char == "_":
            safe_chars.append(char)
            previous_was_separator = False
        elif not previous_was_separator:
            safe_chars.append("-")
            previous_was_separator = True

    safe_id = "".join(safe_chars).strip("-_")
    return safe_id or "sp2-pack"


def _default_pack_title(source_path: Path) -> str:
    """Derive a title from the selected file or directory name."""
    source_name = source_path.stem if source_path.is_file() else source_path.name
    return source_name.strip() or source_path.name


def _embedding_dimension(embedded_chunks: list[EmbeddedChunk]) -> int:
    """Validate bundle vectors and return their shared dimension."""
    if not embedded_chunks:
        raise ValueError("Bundle sources produced no chunks to write")

    embedding_dim = len(embedded_chunks[0].vector)
    if embedding_dim <= 0:
        raise ValueError("Bundle embedding vectors must not be empty")

    for chunk in embedded_chunks:
        if len(chunk.vector) != embedding_dim:
            raise ValueError(
                "Bundle embedding dimension mismatch: "
                f"expected={embedding_dim}, "
                f"chunk_id={chunk.chunk_id!r}, actual={len(chunk.vector)}"
            )
    return embedding_dim


def _finalize_pack(
    *,
    embedded_chunks: list[EmbeddedChunk],
    metadata: PackMetadata,
    final_zip_path: str | Path,
) -> None:
    """Write and atomically publish one completed course-pack zip."""
    destination = Path(final_zip_path).expanduser().resolve()
    with TemporaryDirectory(
        dir=destination.parent,
        prefix=f".{destination.stem}-",
    ) as temporary_dir:
        staging_root = Path(temporary_dir)
        staging_pack_dir = staging_root / "pack"
        staging_zip_path = staging_root / destination.name

        write_pack_directory(
            staging_pack_dir,
            metadata=metadata,
            embedded_chunks=embedded_chunks,
        )
        export_pack_zip(staging_pack_dir, staging_zip_path)
        staging_zip_path.replace(destination)
