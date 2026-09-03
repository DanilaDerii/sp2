"""DOCX text extraction worker."""

from pathlib import Path

from ...common.models import ExtractedDocument, ExtractedPage


def _extract_docx_with_pandoc(source_path: Path) -> str:
    """Extract plain text from a DOCX file with Pandoc."""
    try:
        import pypandoc
    except ImportError as exc:
        raise RuntimeError(
            "DOCX extraction requires pypandoc_binary from environment/requirements.txt"
        ) from exc

    try:
        return pypandoc.convert_file(
            source_path,
            "plain",
            format="docx",
            extra_args=["--wrap=none"],
        ).strip()
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(f"Pandoc failed to extract text from {source_path.name}: {exc}") from exc


def extract_docx_text(docx_path: str | Path) -> ExtractedDocument:
    """Extract normalized text from a DOCX document."""
    source_path = Path(docx_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"DOCX not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")
    if source_path.suffix.lower() != ".docx":
        raise ValueError(f"Expected a DOCX file, got: {source_path.name}")

    full_text = _extract_docx_with_pandoc(source_path)
    if not full_text:
        raise RuntimeError(f"Pandoc extracted no text from {source_path.name}")

    pages = [ExtractedPage(page_number=None, text=full_text)]
    return ExtractedDocument(
        source_path=str(source_path),
        page_count=len(pages),
        pages=pages,
    )
