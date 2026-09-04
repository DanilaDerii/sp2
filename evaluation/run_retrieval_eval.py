"""Score SP2 retrieval context against the ml.pdf page-grounded evaluation set."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from storage.cruds.lancedb.connection import get_pack_chunks_table
from storage.cruds.sqlite.pack_repository import get_installed_pack
from student.domain.retrieval.chunk_search import (
    DEFAULT_MAX_DISTANCE,
    _row_to_retrieved_chunk,
    _within_max_distance,
)
from student.domain.retrieval.chunk_selector import select_chunks_with_trace
from student.domain.retrieval.models import RetrievedChunk
from student.domain.retrieval.query_embedder import embed_question_for_pack


DEFAULT_DATASET = REPO_ROOT / "evaluation" / "ml_pdf_eval_200.jsonl"
DEFAULT_HISTORY = REPO_ROOT / "evaluation" / "ml_pdf_eval_progress.jsonl"

REASON_GUIDE = {
    "not_in_raw_top_20": {
        "meaning": "Vector search did not find the expected evidence in its raw top 20 candidates.",
        "likely_next_change": "Evaluate hybrid retrieval, embeddings, or chunking.",
    },
    "distance_threshold": {
        "meaning": "Vector search found the expected evidence, but the relevance distance threshold removed it.",
        "likely_next_change": "Tune the relevance threshold separately from ranking.",
    },
    "short_chunk_cap": {
        "meaning": "The selector removed the expected evidence after its short-chunk allowance was filled.",
        "likely_next_change": "Improve title and short-chunk selection rules.",
    },
    "near_duplicate": {
        "meaning": "The selector treated the expected evidence as near-duplicate text.",
        "likely_next_change": "Audit and tune duplicate detection.",
    },
    "below_final_five": {
        "meaning": "Evidence was in the raw candidate pool but did not reach final context after five chunks were selected.",
        "likely_next_change": "Evaluate a reranker over the top 20 candidates.",
    },
    "backend_selection_mismatch": {
        "meaning": "The local diagnostic selected evidence that the live backend did not return.",
        "likely_next_change": "Verify that the backend is running the same retrieval revision before tuning.",
    },
}


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


def _raw_vector_candidates(
    installed_pack: object,
    pack_id: int,
    question: str,
    candidate_k: int,
) -> list[RetrievedChunk]:
    """Return the raw LanceDB candidates in vector-distance order."""
    query_embedding = embed_question_for_pack(question, installed_pack)
    rows = (
        get_pack_chunks_table()
        .search(query_embedding.vector)
        .where(f"installed_pack_id = {pack_id}", prefilter=True)
        .limit(candidate_k)
        .to_list()
    )
    return [_row_to_retrieved_chunk(row) for row in rows]


def _candidate_trace(candidates: list[RetrievedChunk], top_k: int) -> tuple[list[RetrievedChunk], list[dict]]:
    """Run production selection rules and return a complete evaluator trace."""
    within_distance = [
        candidate for candidate in candidates if _within_max_distance(candidate, DEFAULT_MAX_DISTANCE)
    ]
    selected, selection_traces = select_chunks_with_trace(within_distance, top_k=top_k)
    selection_by_id = {trace.chunk.chunk_id: trace for trace in selection_traces}
    trace: list[dict] = []
    for raw_rank, candidate in enumerate(candidates, start=1):
        if not _within_max_distance(candidate, DEFAULT_MAX_DISTANCE):
            decision = "distance_threshold"
            final_rank = None
            selector_candidate_rank = None
            word_count = len(candidate.text.split())
        else:
            selection = selection_by_id[candidate.chunk_id]
            decision = selection.decision
            final_rank = selection.final_rank
            selector_candidate_rank = selection.candidate_rank
            word_count = selection.word_count
        trace.append(
            {
                "raw_rank": raw_rank,
                "selector_candidate_rank": selector_candidate_rank,
                "chunk_id": candidate.chunk_id,
                "page": candidate.page,
                "distance": candidate.distance,
                "word_count": word_count,
                "decision": decision,
                "final_rank": final_rank,
            }
        )
    return selected, trace


def _primary_miss_reason(expected_pages: list[int], trace: list[dict], backend_pages: list[int]) -> str:
    relevant = [item for item in trace if item["page"] in set(expected_pages)]
    if not relevant:
        return "not_in_raw_top_20"
    first_relevant = relevant[0]
    decision = first_relevant["decision"]
    if decision == "distance_threshold":
        return "distance_threshold"
    if decision == "short_chunk_cap":
        return "short_chunk_cap"
    if decision == "near_duplicate":
        return "near_duplicate"
    if decision == "not_examined_final_limit":
        return "below_final_five"
    if decision == "selected" and first_relevant["page"] not in backend_pages:
        return "backend_selection_mismatch"
    return "below_final_five"


def _chunk_catalog_entry(chunk: RetrievedChunk) -> dict:
    return {
        "page": chunk.page,
        "section": chunk.section,
        "source_title": chunk.source_title,
        "text": chunk.text,
    }


def _load_samples(path: Path, split: str | None, all_samples: bool) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not rows or "_metadata" not in rows[0]:
        raise ValueError("Dataset must begin with a metadata JSONL record")
    samples = rows[1:] if all_samples else [row for row in rows[1:] if row.get("split") == split]
    if not samples:
        selection = "entire dataset" if all_samples else f"split: {split}"
        raise ValueError(f"No samples found for {selection}")
    return samples


def _git_revision() -> str:
    """Return the code revision evaluated, without failing outside Git."""
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _append_history(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as history:
        history.write(json.dumps(record, ensure_ascii=True) + "\n")


def _first_relevant_rank(pages: list[int], expected_pages: list[int]) -> int | None:
    expected = set(expected_pages)
    for rank, page in enumerate(pages, start=1):
        if page in expected:
            return rank
    return None


def _ndcg_at_k(pages: list[int], expected_pages: list[int], k: int) -> float:
    expected = set(expected_pages)
    dcg = sum(
        1 / math.log2(rank + 1)
        for rank, page in enumerate(pages[:k], start=1)
        if page in expected
    )
    ideal_hits = min(len(expected), k)
    ideal_dcg = sum(1 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate SP2 page retrieval for ml.pdf")
    parser.add_argument("--pack-id", type=int, required=True, help="Installed SP2 pack ID for ml.pdf")
    parser.add_argument("--split", choices=("val", "test"), default="test")
    parser.add_argument(
        "--all-samples",
        action="store_true",
        help="Evaluate every record in a single-document dataset",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--candidate-k",
        type=int,
        default=20,
        help="Raw vector candidates used for Recall@20",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--report", type=Path, help="Optional JSON report destination")
    parser.add_argument(
        "--history",
        type=Path,
        default=DEFAULT_HISTORY,
        help="Append a compact progress record here after this run",
    )
    parser.add_argument(
        "--no-history",
        action="store_false",
        dest="record_history",
        help="Do not append this run to the progress history",
    )
    args = parser.parse_args()

    samples = _load_samples(args.dataset, args.split, args.all_samples)
    installed_pack = get_installed_pack(args.pack_id)
    if installed_pack is None:
        raise RuntimeError(f"Installed pack not found: {args.pack_id}")
    results: list[dict] = []
    chunk_catalog: dict[str, dict] = {}
    embedding_models: set[str] = set()
    for sample in samples:
        packet = _request_context(args.base_url, args.pack_id, sample["question"], args.top_k)
        embedding_model = packet.get("embedding_model")
        if isinstance(embedding_model, str):
            embedding_models.add(embedding_model)
        pages = [int(chunk["page"]) for chunk in packet.get("chunks", []) if chunk.get("page") is not None]
        expected_pages = sample["supporting_pages"]
        raw_candidates = _raw_vector_candidates(
            installed_pack, args.pack_id, sample["question"], args.candidate_k
        )
        diagnostic_selected, candidate_trace = _candidate_trace(raw_candidates, args.top_k)
        for candidate in raw_candidates:
            chunk_catalog.setdefault(candidate.chunk_id, _chunk_catalog_entry(candidate))
        raw_candidate_pages = [candidate.page for candidate in raw_candidates if candidate.page is not None]
        diagnostic_selected_ids = [candidate.chunk_id for candidate in diagnostic_selected]
        backend_selected_ids = [chunk["chunk_id"] for chunk in packet.get("chunks", [])]
        first_relevant_rank = (
            _first_relevant_rank(pages, expected_pages) if sample["answerable"] else None
        )
        page_hit = first_relevant_rank is not None
        candidate_hit = (
            bool(set(raw_candidate_pages) & set(expected_pages)) if sample["answerable"] else None
        )
        primary_miss_reason = (
            _primary_miss_reason(expected_pages, candidate_trace, pages)
            if sample["answerable"] and not page_hit
            else None
        )
        results.append(
            {
                "id": sample["id"],
                "answerable": sample["answerable"],
                "question": sample["question"],
                "expected_pages": expected_pages,
                "retrieved_pages": pages,
                "raw_vector_candidate_pages": raw_candidate_pages,
                "candidate_trace": candidate_trace,
                "diagnostic_selected_chunk_ids": diagnostic_selected_ids,
                "backend_selected_chunk_ids": backend_selected_ids,
                "diagnostic_matches_backend": diagnostic_selected_ids == backend_selected_ids,
                "page_hit": page_hit,
                "raw_vector_candidate_hit": candidate_hit,
                "first_relevant_rank": first_relevant_rank,
                "ndcg_at_5": _ndcg_at_k(pages, expected_pages, 5) if sample["answerable"] else None,
                "citation_ready": page_hit,
                "mode": packet.get("mode"),
                "primary_miss_reason": primary_miss_reason,
            }
        )

    answerable = [result for result in results if result["answerable"]]
    unanswerable = [result for result in results if not result["answerable"]]
    miss_reason_counts = Counter(
        result["primary_miss_reason"]
        for result in answerable
        if result["primary_miss_reason"] is not None
    )
    misses = [result for result in answerable if result["primary_miss_reason"] is not None]
    summary = {
        "split": "all" if args.all_samples else args.split,
        "sample_count": len(results),
        "top_k": args.top_k,
        "candidate_k": args.candidate_k,
        "recall_at_5": sum(result["page_hit"] for result in answerable) / len(answerable),
        "raw_vector_recall_at_20": (
            sum(result["raw_vector_candidate_hit"] for result in answerable) / len(answerable)
        ),
        "mrr": sum(1 / result["first_relevant_rank"] for result in answerable if result["first_relevant_rank"] is not None) / len(answerable),
        "ndcg_at_5": sum(result["ndcg_at_5"] for result in answerable) / len(answerable),
        "citation_ready_rate": sum(result["citation_ready"] for result in answerable) / len(answerable),
        "miss_reason_counts": dict(sorted(miss_reason_counts.items())),
        "diagnostic_backend_match_rate": (
            sum(result["diagnostic_matches_backend"] for result in results) / len(results)
        ),
        "unanswerable_no_context_rate": (
            sum(result["mode"] == "no_course_context" for result in unanswerable) / len(unanswerable)
            if unanswerable
            else None
        ),
    }
    run = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "pack_id": args.pack_id,
        "split": "all" if args.all_samples else args.split,
        "top_k": args.top_k,
        "candidate_k": args.candidate_k,
        "embedding_models": sorted(embedding_models),
    }
    report = {
        "run": run,
        "summary": summary,
        "reason_guide": REASON_GUIDE,
        "misses": misses,
        "results": results,
        "chunk_catalog": chunk_catalog,
    }
    print(json.dumps(summary, indent=2))
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote report to {args.report}")
    if args.record_history:
        _append_history(args.history, {"run": run, "summary": summary})
        print(f"Appended progress record to {args.history}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
