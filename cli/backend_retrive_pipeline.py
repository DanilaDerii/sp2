"""Command-line client for the student retrieval backend route."""

from __future__ import annotations

import argparse
import json

from integrations.lm_studio_mcp.client import request_backend_json


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ask the running SP2 backend to retrieve course-pack chunks.",
    )
    parser.add_argument(
        "installed_pack_id",
        type=_positive_int,
        help="Local installed pack ID to search.",
    )
    parser.add_argument(
        "question",
        help="Student question to embed and search for.",
    )
    parser.add_argument("--top-k", type=_positive_int, default=None)
    parser.add_argument("--max-distance", type=_non_negative_float, default=None)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    payload = {
        "installed_pack_id": args.installed_pack_id,
        "question": args.question,
    }
    if args.top_k is not None:
        payload["top_k"] = args.top_k
    if args.max_distance is not None:
        payload["max_distance"] = args.max_distance

    response = request_backend_json(
        "POST",
        "/retrieval/context",
        json_body=payload,
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
