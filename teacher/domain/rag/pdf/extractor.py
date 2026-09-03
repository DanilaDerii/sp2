"""PDF text extraction worker."""

from pathlib import Path

import pymupdf

from ..common.models import ExtractedDocument, ExtractedPage


def _extract_pdf_text_with_pymupdf(source_path: Path) -> ExtractedDocument:
    pages: list[ExtractedPage] = []
    try:
        with pymupdf.open(str(source_path)) as document:
            for page_number, page in enumerate(document, start=1):
                page_text = page.get_text("text", sort=True).strip()
                pages.append(
                    ExtractedPage(
                        page_number=page_number,
                        text=page_text,
                    )
                )
    except Exception as exc:
        raise RuntimeError(
            f"PyMuPDF failed to extract text from {source_path.name}: {exc}"
        ) from exc

    if not any(page.text for page in pages):
        raise RuntimeError(f"PyMuPDF extracted no text from {source_path.name}")

    return ExtractedDocument(
        source_path=str(source_path),
        page_count=len(pages),
        pages=pages,
    )


def extract_pdf_text(pdf_path: str | Path) -> ExtractedDocument:
    """Extract page text from a PDF."""
    source_path = Path(pdf_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {source_path.name}")

    return _extract_pdf_text_with_pymupdf(source_path)
