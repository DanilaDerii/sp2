"""ODT text extraction worker."""

from pathlib import Path

from ...common.models import ExtractedDocument, ExtractedPage


def _extract_odt_with_pandoc(source_path: Path) -> str:
    """Extract plain text from an ODT file with Pandoc."""
    try:
        import pypandoc
    except ImportError as exc:
        raise RuntimeError(
            "ODT extraction requires pypandoc_binary from environment/requirements.txt"
        ) from exc

    try:
        return pypandoc.convert_file(
            source_path,
            "plain",
            format="odt",
            extra_args=["--wrap=none"],
        ).strip()
    except (OSError, RuntimeError) as exc:
        raise RuntimeError(f"Pandoc failed to extract text from {source_path.name}: {exc}") from exc


def extract_odt_text(odt_path: str | Path) -> ExtractedDocument:
    """Extract normalized text from an ODT document."""
    source_path = Path(odt_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"ODT not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")
    if source_path.suffix.lower() != ".odt":
        raise ValueError(f"Expected an ODT file, got: {source_path.name}")

    full_text = _extract_odt_with_pandoc(source_path)
    if not full_text:
        raise RuntimeError(f"Pandoc extracted no text from {source_path.name}")

    pages = [ExtractedPage(page_number=1, text=full_text)]
    return ExtractedDocument(
        source_path=str(source_path),
        page_count=len(pages),
        pages=pages,
    )
