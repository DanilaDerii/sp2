"""Docling-based PDF text extraction worker."""

from pathlib import Path

from docling.datamodel.base_models import ConversionStatus
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from ..common.models import ExtractedDocument, ExtractedPage


def extract_pdf_text(pdf_path: str | Path) -> ExtractedDocument:
    """Extract document text and page text from a PDF with Docling."""
    source_path = Path(pdf_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {source_path.name}")

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    converter = DocumentConverter(
        format_options={
            "pdf": PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    result = converter.convert(source_path)

    if result.status is not ConversionStatus.SUCCESS:
        error_messages = [error.message for error in result.errors]
        raise RuntimeError(
            "Docling conversion failed for "
            f"{source_path.name}: {'; '.join(error_messages) or result.status.value}"
        )

    document = result.document
    page_numbers = sorted(document.pages.keys())
    pages: list[ExtractedPage] = []
    for page_number in page_numbers:
        page_text = document.export_to_text(
            page_no=page_number,
            page_break_placeholder=None,
            traverse_pictures=True,
        ).strip()
        pages.append(
            ExtractedPage(
                page_number=page_number,
                text=page_text,
            )
        )

    full_text = document.export_to_text(
        page_break_placeholder=None,
        traverse_pictures=True,
    ).strip()
    markdown = document.export_to_markdown(
        page_break_placeholder=None,
        traverse_pictures=True,
    ).strip()

    return ExtractedDocument(
        source_path=str(source_path),
        source_name=source_path.name,
        page_count=len(page_numbers),
        text=full_text,
        markdown=markdown,
        pages=pages,
    )

