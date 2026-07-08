"""ODT text extraction worker."""

from pathlib import Path

from ...common.models import ExtractedDocument, ExtractedPage


def _convert_odt_with_pandoc(source_path: Path, output_format: str) -> str:
    """Convert an ODT file to text-like content with Pandoc."""
    try:
        import pypandoc
    except ImportError as exc:
        raise RuntimeError(
            "ODT extraction requires pypandoc_binary from environment/requirements.txt"
        ) from exc

    try:
        return pypandoc.convert_file(
            source_path,
            output_format,
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

    full_text = _convert_odt_with_pandoc(source_path, "plain")
    if not full_text:
        raise RuntimeError(f"Pandoc extracted no text from {source_path.name}")

    markdown = _convert_odt_with_pandoc(source_path, "gfm")
    if not markdown:
        markdown = full_text

    pages = [ExtractedPage(page_number=1, text=full_text)]
    return ExtractedDocument(
        source_path=str(source_path),
        source_name=source_path.name,
        page_count=len(pages),
        text=full_text,
        markdown=markdown,
        pages=pages,
    )
