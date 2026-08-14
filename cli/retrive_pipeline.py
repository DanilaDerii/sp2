"""Command-line runner for the student retrieval pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from student.domain.retrieval.context_builder import build_course_context_packet


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
        description=(
            "Embed one student question with LM Studio and return relevant chunks "
            "from one installed course pack."
        ),
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
    parser.add_argument(
        "--top-k",
        type=_positive_int,
        default=None,
        help="Maximum number of chunks to return. Uses the pack default when omitted.",
    )
    parser.add_argument(
        "--max-distance",
        type=_non_negative_float,
        default=None,
        help="Maximum LanceDB distance. Uses the retrieval default when omitted.",
    )
    return parser


def main() -> None:
    """Run the student question-embedding and chunk-retrieval pipeline."""
    args = _build_parser().parse_args()
    packet = build_course_context_packet(
        installed_pack_id=args.installed_pack_id,
        question=args.question,
        top_k=args.top_k,
        max_distance=args.max_distance,
    )
    print(json.dumps(asdict(packet), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
