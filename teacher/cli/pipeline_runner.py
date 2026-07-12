"""Command-line runner for the teacher pack build pipeline."""

import argparse
from pathlib import Path

from teacher.domain.rag.common.pipeline import build_pack_from_source
from teacher.domain.rag.pdf.extractor import extract_pdf_text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a teacher course pack from one PDF file.",
    )
    parser.add_argument(
        "pdf_path",
        help="Path to the PDF file to ingest.",
    )
    return parser


def main() -> None:
    """Run the teacher pipeline from a single PDF path argument."""
    args = _build_parser().parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()

    result = build_pack_from_source(
        pdf_path,
        extract_document=extract_pdf_text,
        source_type="pdf",
    )

    print("Teacher pipeline completed")
    print(f"source: {pdf_path}")
    print(f"pack_id: {result.metadata.pack_id}")
    print(f"title: {result.metadata.title}")
    print(f"pages: {result.extracted_document.page_count}")
    print(f"chunks: {len(result.chunks)}")
    print(f"embedding_model: {result.metadata.embedding_model}")
    print(f"embedding_dim: {result.metadata.embedding_dim}")
    print(f"pack_dir: {result.pack_directory}")
    print(f"zip_path: {result.zip_path}")


if __name__ == "__main__":
    main()
