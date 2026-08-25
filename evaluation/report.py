"""Writes eval results as JSON and a human-readable markdown report."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from evaluation.runner import EvalResult, ModelResult


def _format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "unknown"
    return f"{size_bytes / (1024 ** 3):.2f} GB"


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _model_summary_row(model: ModelResult) -> dict[str, str]:
    latencies = [q.latency_seconds for q in model.questions if q.latency_seconds is not None]
    speeds = [q.tokens_per_second for q in model.questions if q.tokens_per_second is not None]
    succeeded = sum(1 for q in model.questions if q.error is None)
    total = len(model.questions)

    avg_latency = _average(latencies)
    avg_speed = _average(speeds)

    return {
        "model": model.model_key,
        "size": _format_size(model.size_bytes),
        "avg_latency": f"{avg_latency:.2f}s" if avg_latency is not None else "n/a",
        "avg_tokens_per_second": f"{avg_speed:.1f}" if avg_speed is not None else "n/a",
        "answered": f"{succeeded}/{total}",
    }


def _write_json(eval_result: EvalResult, out_dir: Path) -> Path:
    json_path = out_dir / "results.json"
    json_path.write_text(
        json.dumps(asdict(eval_result), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return json_path


def _write_markdown(eval_result: EvalResult, out_dir: Path) -> Path:
    lines: list[str] = [
        f"# Chat model comparison — installed pack {eval_result.installed_pack_id}",
        "",
        "## Summary",
        "",
        "| Model | Size | Avg latency | Avg tokens/sec | Answered |",
        "| --- | --- | --- | --- | --- |",
    ]
    for model in eval_result.models:
        row = _model_summary_row(model)
        lines.append(
            f"| {row['model']} | {row['size']} | {row['avg_latency']} "
            f"| {row['avg_tokens_per_second']} | {row['answered']} |"
        )
    lines.append("")

    questions = [q.question for q in eval_result.models[0].questions] if eval_result.models else []
    for question in questions:
        lines.append(f"## {question}")
        lines.append("")
        for model in eval_result.models:
            match = next((q for q in model.questions if q.question == question), None)
            lines.append(f"### {model.model_key}")
            if match is None:
                lines.append("_no result_")
            elif match.error is not None:
                lines.append(f"**Error:** {match.error}")
            else:
                stats = []
                if match.latency_seconds is not None:
                    stats.append(f"{match.latency_seconds:.2f}s")
                if match.tokens_per_second is not None:
                    stats.append(f"{match.tokens_per_second:.1f} tok/s")
                stats.append(f"{match.chunk_count} chunks retrieved")
                lines.append(f"*({', '.join(stats)})*")
                lines.append("")
                lines.append(match.answer or "")
            lines.append("")

    markdown_path = out_dir / "results.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return markdown_path


def write_report(eval_result: EvalResult, out_dir: Path) -> tuple[Path, Path]:
    """Write results.json and results.md into out_dir, creating it if needed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = _write_json(eval_result, out_dir)
    markdown_path = _write_markdown(eval_result, out_dir)
    return json_path, markdown_path


def default_report_dir(base_dir: Path) -> Path:
    """Return a fresh timestamped report directory under base_dir."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return base_dir / timestamp
