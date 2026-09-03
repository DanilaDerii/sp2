"""Command-line runner for the teacher pack build pipeline."""

import argparse
from pathlib import Path

from teacher.domain.orchestrators.bundle_parsing import build_pack_from_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a teacher course pack from one supported file or from all supported "
            "files below a directory."
        ),
    )
    parser.add_argument(
        "source_path",
        help=(
            "Path to a PDF, ODT, DOCX, or PPTX file, or a directory "
            "containing those files."
        ),
    )
    return parser


def main() -> None:
    """Run the single-file or directory teacher pack pipeline."""
    args = _build_parser().parse_args()
    source_path = Path(args.source_path).expanduser().resolve()

    result = build_pack_from_path(source_path)

    print("Teacher pipeline completed")
    print(f"source: {source_path}")
    print(f"pack_id: {result.metadata.pack_id}")
    print(f"title: {result.metadata.title}")
    print(f"pages: {result.page_count}")
    print(f"chunks: {result.chunk_count}")
    print(f"embedding_model: {result.metadata.embedding_model}")
    print(f"embedding_dim: {result.metadata.embedding_dim}")
    print(f"zip_path: {result.zip_path}")


if __name__ == "__main__":
    main()
