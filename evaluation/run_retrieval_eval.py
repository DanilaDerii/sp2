"""Score SP2 retrieval context against the ml.pdf page-grounded evaluation set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "evaluation" / "ml_pdf_eval_200.jsonl"


def _request_context(base_url: str, pack_id: int, question: str, top_k: int) -> dict:
    request = Request(
        f"{base_url.rstrip('/')}/retrieval/context",
        data=json.dumps(
            {
                "installed_pack_id": pack_id,
                "question": question,
                "top_k": top_k,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Backend returned HTTP {exc.code}: {exc.read().decode('utf-8')}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach SP2 backend: {exc.reason}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("SP2 backend returned a non-object context response")
    return payload


def _load_samples(path: Path, split: str) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or "_metadata" not in rows[0]:
        raise ValueError("Dataset must begin with a metadata JSONL record")
    samples = [row for row in rows[1:] if row["split"] == split]
    if not samples:
        raise ValueError(f"No samples found for split: {split}")
    return samples


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SP2 page retrieval for ml.pdf")
    parser.add_argument("--pack-id", type=int, required=True, help="Installed SP2 pack ID for ml.pdf")
    parser.add_argument("--split", choices=("train", "val", "test"), default="test")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, help="Optional JSON report destination")
    args = parser.parse_args()

    samples = _load_samples(args.dataset, args.split)
    results: list[dict] = []
    for sample in samples:
        packet = _request_context(args.base_url, args.pack_id, sample["question"], args.top_k)
        pages = sorted({chunk["page"] for chunk in packet.get("chunks", []) if chunk.get("page") is not None})
        expected_pages = sample["supporting_pages"]
        page_hit = bool(set(pages) & set(expected_pages)) if sample["answerable"] else None
        results.append(
            {
                "id": sample["id"],
                "answerable": sample["answerable"],
                "question": sample["question"],
                "expected_pages": expected_pages,
                "retrieved_pages": pages,
                "page_hit": page_hit,
                "citation_ready": page_hit,
                "mode": packet.get("mode"),
            }
        )

    answerable = [result for result in results if result["answerable"]]
    unanswerable = [result for result in results if not result["answerable"]]
    summary = {
        "split": args.split,
        "sample_count": len(results),
        "top_k": args.top_k,
        "retrieval_recall_at_k": sum(result["page_hit"] for result in answerable) / len(answerable),
        "citation_ready_rate": sum(result["citation_ready"] for result in answerable) / len(answerable),
        "unanswerable_no_context_rate": (
            sum(result["mode"] == "no_course_context" for result in unanswerable) / len(unanswerable)
            if unanswerable
            else None
        ),
    }
    report = {"summary": summary, "results": results}
    print(json.dumps(summary, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote report to {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
