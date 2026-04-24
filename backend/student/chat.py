"""Student-side chat orchestration over retrieved pack context."""

from dataclasses import dataclass

import httpx

from backend.student.retrieval import (
    DEFAULT_RETRIEVAL_TOP_K,
    RetrievedChunk,
    retrieve_chunks_for_question,
)
from backend.teacher.rag.embedder import DEFAULT_OLLAMA_BASE_URL

DEFAULT_CHAT_MODEL = "qwen2.5:3b"
DEFAULT_CHAT_TEMPERATURE = 0.2
RETRIEVAL_DISTANCE_DEBUG_THRESHOLD = 1.2


@dataclass(slots=True)
class ChatResponse:
    """Student-facing answer plus the retrieved supporting chunks."""

    pack_id: str
    question: str
    answer: str
    used_debug_fallback: bool
    retrieved_chunks: list[RetrievedChunk]


def _build_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks into a compact prompt context block."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        location = f"page={chunk.page}" if chunk.page else "page=unknown"
        parts.append(
            "\n".join(
                [
                    f"[Chunk {index}]",
                    f"source_title={chunk.source_title}",
                    f"source_type={chunk.source_type}",
                    f"{location}",
                    f"text={chunk.text}",
                ]
            )
        )
    return "\n\n".join(parts)


def _build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Build the grounded prompt sent to the local generation model."""
    context = _build_context(chunks)
    return (
        "You are a course assistant answering only from the provided course-pack context.\n"
        "If the context is insufficient, say clearly that the answer is not in the database.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{context}\n\n"
        "Answer using the context as directly as possible."
    )


def _should_use_debug_fallback(chunks: list[RetrievedChunk]) -> bool:
    """Decide whether retrieval looks too weak to trust for an answer."""
    if not chunks:
        return True

    best_distance = chunks[0].distance
    if best_distance is None:
        return False
    return best_distance > RETRIEVAL_DISTANCE_DEBUG_THRESHOLD


def _generate_answer(
    prompt: str,
    *,
    model: str = DEFAULT_CHAT_MODEL,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> str:
    """Call the local Ollama generation model with the grounded prompt."""
    with httpx.Client(base_url=ollama_base_url, timeout=120.0) as client:
        response = client.post(
            "/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": DEFAULT_CHAT_TEMPERATURE},
            },
        )
        response.raise_for_status()
        payload = response.json()
        answer = payload.get("response", "").strip()
        if not answer:
            raise RuntimeError("Ollama generation returned an empty response")
        return answer


def answer_question(
    question: str,
    pack_id: str,
    *,
    top_k: int = DEFAULT_RETRIEVAL_TOP_K,
    embedding_model: str = "all-minilm:latest",
    chat_model: str = DEFAULT_CHAT_MODEL,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> ChatResponse:
    """Run retrieval plus answer generation for one student question."""
    retrieval = retrieve_chunks_for_question(
        question,
        pack_id,
        top_k=top_k,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url,
    )

    use_debug_fallback = _should_use_debug_fallback(retrieval.chunks)
    if use_debug_fallback:
        return ChatResponse(
            pack_id=pack_id,
            question=retrieval.question,
            answer="This is not in the database.",
            used_debug_fallback=True,
            retrieved_chunks=retrieval.chunks,
        )

    answer = _generate_answer(
        _build_prompt(retrieval.question, retrieval.chunks),
        model=chat_model,
        ollama_base_url=ollama_base_url,
    )
    return ChatResponse(
        pack_id=pack_id,
        question=retrieval.question,
        answer=answer,
        used_debug_fallback=False,
        retrieved_chunks=retrieval.chunks,
    )
