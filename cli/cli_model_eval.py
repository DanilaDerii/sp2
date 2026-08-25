"""Command-line entry point for the chat model comparison harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from config.arguments import ARTIFACTS_DIR
from evaluation.report import default_report_dir, write_report
from evaluation.runner import run_evaluation

DEFAULT_QUESTIONS_PATH = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "sample_questions"
    / "kitchen_equipment_questions.json"
)
DEFAULT_MODEL_KEYS = (
    "qwen2.5-3b-instruct,"
    "llama-3.2-3b-instruct,"
    "phi-3.5-mini-instruct,"
    "qwen2.5-coder-3b-instruct"
)


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return number


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare candidate LM Studio chat models on how well they answer "
            "questions grounded in one installed course pack's retrieved chunks."
        ),
    )
    parser.add_argument(
        "--pack",
        dest="installed_pack_id",
        type=_positive_int,
        required=True,
        help="Installed pack ID to retrieve course context from.",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=DEFAULT_QUESTIONS_PATH,
        help="Path to a JSON file containing a list of question strings.",
    )
    parser.add_argument(
        "--models",
        default=DEFAULT_MODEL_KEYS,
        help="Comma-separated LM Studio model keys to compare, one at a time.",
    )
    parser.add_argument(
        "--top-k",
        type=_positive_int,
        default=None,
        help="Override the pack's default retrieval top_k.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    model_keys = [key.strip() for key in args.models.split(",") if key.strip()]

    eval_result = run_evaluation(
        args.installed_pack_id,
        questions,
        model_keys,
        top_k=args.top_k,
    )

    out_dir = default_report_dir(ARTIFACTS_DIR / "model_eval")
    json_path, markdown_path = write_report(eval_result, out_dir)

    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
