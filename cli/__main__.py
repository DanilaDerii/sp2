"""Command-line client for every SP2 backend API route."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from integrations.backend_api import request_backend_json


CommandHandler = Callable[[argparse.Namespace], Any]


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return number


def _non_negative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value must be greater than or equal to 0")
    return number


def _health(_: argparse.Namespace) -> Any:
    return request_backend_json("GET", "/health")


def _list_packs(args: argparse.Namespace) -> Any:
    params: dict[str, Any] = {}
    if args.pack_id is not None:
        params["pack_id"] = args.pack_id
    if args.active_only:
        params["active_only"] = True
    return request_backend_json("GET", "/packs", params=params)


def _get_pack(args: argparse.Namespace) -> Any:
    return request_backend_json("GET", f"/packs/{args.installed_pack_id}")


def _delete_pack(args: argparse.Namespace) -> Any:
    if not args.yes:
        raise RuntimeError(
            "Deletion was not sent. Add --yes if you really want to delete this pack."
        )
    return request_backend_json("DELETE", f"/packs/{args.installed_pack_id}")


def _install(args: argparse.Namespace) -> Any:
    source_path = Path(args.source_path).expanduser().resolve()
    return request_backend_json(
        "POST",
        "/ingest/source",
        json_body={"source_path": str(source_path)},
    )


def _context(args: argparse.Namespace) -> Any:
    payload: dict[str, Any] = {
        "installed_pack_id": args.installed_pack_id,
        "question": args.question,
    }
    if args.top_k is not None:
        payload["top_k"] = args.top_k
    if args.max_distance is not None:
        payload["max_distance"] = args.max_distance
    return request_backend_json("POST", "/retrieval/context", json_body=payload)


def _file_summary(args: argparse.Namespace) -> Any:
    return request_backend_json(
        "POST",
        "/summaries/file-context",
        json_body={
            "installed_pack_id": args.installed_pack_id,
            "source_id": args.source_id,
        },
    )


def _pack_summary(args: argparse.Namespace) -> Any:
    return request_backend_json(
        "POST",
        "/summaries/pack-context",
        json_body={"installed_pack_id": args.installed_pack_id},
    )


def _add_installed_pack_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "installed_pack_id",
        type=_positive_int,
        help="Exact numeric ID returned by the packs command.",
    )


def _command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
    handler: CommandHandler,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text, description=help_text)
    parser.set_defaults(handler=handler)
    return parser


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cli",
        description="Call and test the running SP2 backend API.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    _command(subparsers, "health", "Check whether the backend is running.", _health)

    packs_parser = _command(
        subparsers,
        "packs",
        "List installed packs.",
        _list_packs,
    )
    packs_parser.add_argument("--pack-id", help="Filter by the stored pack name.")
    packs_parser.add_argument(
        "--active-only",
        action="store_true",
        help="Return only active packs.",
    )

    get_pack_parser = _command(
        subparsers,
        "pack",
        "Get one installed pack.",
        _get_pack,
    )
    _add_installed_pack_id(get_pack_parser)

    delete_parser = _command(
        subparsers,
        "delete-pack",
        "Delete one installed pack.",
        _delete_pack,
    )
    _add_installed_pack_id(delete_parser)
    delete_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that the pack should be deleted.",
    )

    install_parser = _command(
        subparsers,
        "install",
        "Build or install a course file, directory, or SP2 ZIP pack.",
        _install,
    )
    install_parser.add_argument("source_path", help="Local course source path.")

    context_parser = _command(
        subparsers,
        "context",
        "Retrieve course context for a question.",
        _context,
    )
    _add_installed_pack_id(context_parser)
    context_parser.add_argument("question", help="Question to search for.")
    context_parser.add_argument("--top-k", type=_positive_int)
    context_parser.add_argument("--max-distance", type=_non_negative_float)

    file_summary_parser = _command(
        subparsers,
        "file-summary",
        "Get summary context for one source file.",
        _file_summary,
    )
    _add_installed_pack_id(file_summary_parser)
    file_summary_parser.add_argument("source_id", help="Stored source filename.")

    pack_summary_parser = _command(
        subparsers,
        "pack-summary",
        "Get summary context for one installed pack.",
        _pack_summary,
    )
    _add_installed_pack_id(pack_summary_parser)

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = args.handler(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
