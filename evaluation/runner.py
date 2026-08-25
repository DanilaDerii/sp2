"""Orchestrates the chat-model comparison run.

For each candidate model: load it exclusively, then for each question fetch
the same retrieved chunks the real app would (via the SP2 backend's
/retrieval/context route) and record the model's grounded answer, latency,
and tokens/sec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluation.lm_studio_chat_client import ChatCompletionError, chat_completion
from evaluation.model_switcher import find_lms, installed_model_sizes, switch_to_model
from evaluation.prompts import build_messages
from installation.setup_helpers import SetupError
from integrations.lm_studio_mcp.client import request_backend_json


@dataclass
class QuestionResult:
    """One question's outcome for one candidate model."""

    question: str
    answer: str | None
    error: str | None
    latency_seconds: float | None
    tokens_per_second: float | None
    chunk_count: int
    top_score: float | None


@dataclass
class ModelResult:
    """All question outcomes for one candidate model."""

    model_key: str
    size_bytes: int | None
    questions: list[QuestionResult] = field(default_factory=list)


@dataclass
class EvalResult:
    """The full comparison run across all candidate models."""

    installed_pack_id: int
    models: list[ModelResult] = field(default_factory=list)


def _fetch_context(
    installed_pack_id: int,
    question: str,
    top_k: int | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "installed_pack_id": installed_pack_id,
        "question": question,
    }
    if top_k is not None:
        payload["top_k"] = top_k
    return request_backend_json("POST", "/retrieval/context", json_body=payload)


def run_evaluation(
    installed_pack_id: int,
    questions: list[str],
    model_keys: list[str],
    *,
    top_k: int | None = None,
) -> EvalResult:
    """Run every question through every candidate model and collect results."""
    lms_path = find_lms()
    sizes = installed_model_sizes(lms_path)

    eval_result = EvalResult(installed_pack_id=installed_pack_id)
    previous_identifier: str | None = None

    for model_key in model_keys:
        model_result = ModelResult(model_key=model_key, size_bytes=sizes.get(model_key))

        try:
            switch_to_model(
                lms_path,
                model_key,
                model_key,
                previous_identifier=previous_identifier,
            )
        except SetupError as exc:
            # One model failing to load (LM Studio hiccup, etc.) should not
            # discard results already collected for other models.
            model_result.questions.append(
                QuestionResult(
                    question="(model load failed)",
                    answer=None,
                    error=str(exc),
                    latency_seconds=None,
                    tokens_per_second=None,
                    chunk_count=0,
                    top_score=None,
                )
            )
            eval_result.models.append(model_result)
            continue

        previous_identifier = model_key

        for question in questions:
            chunks: list[dict[str, Any]] = []
            top_score: float | None = None
            try:
                context = _fetch_context(installed_pack_id, question, top_k)
                chunks = context.get("chunks") or []
                top_score = chunks[0].get("score") if chunks else None

                messages = build_messages(question, chunks)
                result = chat_completion(model_key, messages)
                model_result.questions.append(
                    QuestionResult(
                        question=question,
                        answer=result.text,
                        error=None,
                        latency_seconds=result.latency_seconds,
                        tokens_per_second=result.tokens_per_second,
                        chunk_count=len(chunks),
                        top_score=top_score,
                    )
                )
            except (ChatCompletionError, RuntimeError) as exc:
                model_result.questions.append(
                    QuestionResult(
                        question=question,
                        answer=None,
                        error=str(exc),
                        latency_seconds=None,
                        tokens_per_second=None,
                        chunk_count=len(chunks),
                        top_score=top_score,
                    )
                )

        eval_result.models.append(model_result)

    return eval_result
