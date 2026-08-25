"""Grounded prompt construction for the model comparison harness.

Mirrors the grounding instructions already used in the MCP prompt examples
in README.md ("answer using the returned course chunks... if the chunks do
not contain the answer, say so"), so the harness tests models under the same
instruction the real app gives them.
"""

from __future__ import annotations

from typing import Any

SYSTEM_PROMPT = (
    "You are a course assistant. Answer the student's question using only "
    "the course material chunks provided below. If the chunks do not "
    "contain the answer, say so explicitly instead of guessing."
)


def _format_chunk(index: int, chunk: dict[str, Any]) -> str:
    source_title = chunk.get("source_title", "unknown source")
    page = chunk.get("page")
    section = chunk.get("section")

    location_bits = []
    if page is not None:
        location_bits.append(f"page {page}")
    if section:
        location_bits.append(f"section {section}")
    location = f" ({', '.join(location_bits)})" if location_bits else ""

    return f"[{index}] {source_title}{location}:\n{chunk.get('text', '')}"


def build_messages(question: str, chunks: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build the system+user message pair sent to a candidate chat model."""
    if not chunks:
        chunk_block = "(no course material chunks were retrieved for this question)"
    else:
        chunk_block = "\n\n".join(
            _format_chunk(index, chunk) for index, chunk in enumerate(chunks, start=1)
        )

    user_content = (
        f"Course material:\n{chunk_block}\n\nQuestion: {question}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
