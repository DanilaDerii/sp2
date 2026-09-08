"""Command-line client for complete file and pack summary context."""

from __future__ import annotations

import argparse
import json

from integrations.lm_studio_mcp.client import request_backend_json


def _positive_installed_pack_id(value: str) -> int:
    installed_pack_id = int(value)
    if installed_pack_id <= 0:
        raise argparse.ArgumentTypeError("installed_pack_id must be greater than 0")
    return installed_pack_id


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ask the running SP2 backend for every chunk needed to summarize "
            "one source file or one complete installed pack."
        ),
    )
    subparsers = parser.add_subparsers(dest="scope", required=True)

    file_parser = subparsers.add_parser(
        "file",
        help="Return every chunk for one source file.",
    )
    file_parser.add_argument(
        "installed_pack_id",
        type=_positive_installed_pack_id,
        help="Local installed pack ID containing the source file.",
    )
    file_parser.add_argument(
        "source_id",
        help="Exact source_id stored for the file inside the pack.",
    )

    pack_parser = subparsers.add_parser(
        "pack",
        help="Return every chunk from every source in one installed pack.",
    )
    pack_parser.add_argument(
        "installed_pack_id",
        type=_positive_installed_pack_id,
        help="Local installed pack ID to read completely.",
    )

    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = {"installed_pack_id": args.installed_pack_id}

    if args.scope == "file":
        payload["source_id"] = args.source_id
        endpoint = "/summaries/file-context"
    else:
        endpoint = "/summaries/pack-context"

    response = request_backend_json(
        "POST",
        endpoint,
        json_body=payload,
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
