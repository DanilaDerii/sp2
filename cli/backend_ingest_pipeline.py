"""Command-line client for the teacher ingest backend route."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from integrations.lm_studio_mcp.client import request_backend_json


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask the running SP2 backend to build a teacher course pack.",
    )
    parser.add_argument(
        "source_path",
        help="Path to a supported file or a directory containing supported files.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    source_path = Path(args.source_path).expanduser().resolve()
    response = request_backend_json(
        "POST",
        "/ingest/file-path",
        json_body={"file_path": str(source_path)},
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
