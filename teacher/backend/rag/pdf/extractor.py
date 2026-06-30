"""PDF text extraction worker."""

from pathlib import Path
import shutil
import subprocess

from ..common.models import ExtractedDocument, ExtractedPage


def _extract_text_layer_with_pdftotext(pdf_path: Path) -> ExtractedDocument | None:
    pdftotext_path = shutil.which("pdftotext")
    if pdftotext_path is None:
        return None

    completed = subprocess.run(
        [pdftotext_path, "-layout", str(pdf_path), "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None

    raw_pages = completed.stdout.split("\f")
    pages: list[ExtractedPage] = []
    for index, raw_page in enumerate(raw_pages, start=1):
        page_text = raw_page.strip()
        if page_text:
            pages.append(ExtractedPage(page_number=index, text=page_text))

    if not pages:
        return None

    full_text = "\n\n".join(page.text for page in pages)
    return ExtractedDocument(
        source_path=str(pdf_path),
        source_name=pdf_path.name,
        page_count=len(pages),
        text=full_text,
        markdown=full_text,
        pages=pages,
    )


def _extract_pdf_text_with_docling(source_path: Path) -> ExtractedDocument:
    try:
        from docling.datamodel.base_models import ConversionStatus
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise RuntimeError(
            "PDF text-layer extraction failed and Docling is not installed. "
            "Install Docling only when scanned or complex PDFs require it."
        ) from exc

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = False
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
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


def extract_pdf_text(pdf_path: str | Path) -> ExtractedDocument:
    """Extract document text and page text from a PDF."""
    source_path = Path(pdf_path).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"PDF not found: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"Expected a file path, got: {source_path}")
    if source_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got: {source_path.name}")

    extracted_document = _extract_text_layer_with_pdftotext(source_path)
    if extracted_document is not None:
        return extracted_document

    return _extract_pdf_text_with_docling(source_path)
