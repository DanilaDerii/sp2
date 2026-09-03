"""Select useful, varied chunks from a larger semantic-search candidate set.

The current retrieval flow asks LanceDB for exactly the number of chunks that
must be returned to the language model. This can produce weak context when a
pack contains several similar cover pages, chapter outlines, or repeated
headings: those chunks are semantically related to a broad question, so they
can occupy every available result even though more useful explanatory chunks
exist slightly lower in the vector ranking. The intended solution is for
``chunk_search.py`` to retrieve a larger candidate set while preserving vector
distance, then pass those candidates through this module. This module should
remove exact or near-duplicate text, limit repeated low-information title
pages, preserve short chunks when they contain meaningful course information,
and return at most the caller's requested ``top_k`` chunks in relevance order.
It must not change stored vectors, database schemas, API or MCP contracts, and
it should avoid rules based only on text length because short slides such as an
objectives page may still be valuable. Any future selection rules should be
deterministic, independently testable, and conservative so that semantic
retrieval remains the main ranking signal rather than being replaced by a
collection of document-specific keyword rules.

Known limitation, intentionally out of scope: a longer chunk that is generic
or introductory rather than title-only (e.g. "Why learn these kitchen
utensils?") is neither short nor a duplicate, so it is not caught here.
Down-ranking chunks like that would require topical relevance classification,
which is a materially harder problem than the duplicate/title-page
suppression this module handles.
"""

from __future__ import annotations

import math
import re

from config.arguments import (
    DUPLICATE_SIMILARITY_THRESHOLD,
    SHORT_CHUNK_RATIO,
    SHORT_CHUNK_WORD_THRESHOLD,
)

from .models import RetrievedChunk


class ChunkSelectionError(RuntimeError):
    """Raised when chunk selection parameters are invalid."""


_WORD_PATTERN = re.compile(r"\w+")


def _normalized_words(text: str) -> frozenset[str]:
    return frozenset(_WORD_PATTERN.findall(text.lower()))


def _jaccard_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _is_near_duplicate(
    words: frozenset[str],
    selected_words: list[frozenset[str]],
    threshold: float,
) -> bool:
    return any(_jaccard_similarity(words, prior) >= threshold for prior in selected_words)


def _validate_top_k(top_k: int) -> int:
    if isinstance(top_k, bool) or int(top_k) <= 0:
        raise ChunkSelectionError("top_k must be a positive integer")
    return int(top_k)


def _validate_similarity_threshold(value: float) -> float:
    if not (0.0 < float(value) <= 1.0):
        raise ChunkSelectionError("duplicate_similarity_threshold must be in (0, 1]")
    return float(value)


def _default_max_short_chunks(top_k: int) -> int:
    return max(1, math.ceil(top_k * SHORT_CHUNK_RATIO))


def select_chunks(
    candidates: list[RetrievedChunk],
    *,
    top_k: int,
    short_word_threshold: int = SHORT_CHUNK_WORD_THRESHOLD,
    max_short_chunks: int | None = None,
    duplicate_similarity_threshold: float = DUPLICATE_SIMILARITY_THRESHOLD,
) -> list[RetrievedChunk]:
    """Select at most top_k relevant, varied chunks, preserving candidate order.

    Candidates must already be sorted best-first (e.g. by ascending vector
    distance); this function never reorders them, it only skips entries.
    """
    resolved_top_k = _validate_top_k(top_k)
    resolved_threshold = _validate_similarity_threshold(duplicate_similarity_threshold)
    resolved_max_short = (
        max(1, int(max_short_chunks))
        if max_short_chunks is not None
        else _default_max_short_chunks(resolved_top_k)
    )

    selected: list[RetrievedChunk] = []
    selected_words: list[frozenset[str]] = []
    short_count = 0

    for chunk in candidates:
        if len(selected) >= resolved_top_k:
            break

        words = _normalized_words(chunk.text or "")
        if _is_near_duplicate(words, selected_words, resolved_threshold):
            continue

        is_short = len(words) <= short_word_threshold
        if is_short and short_count >= resolved_max_short:
            continue

        selected.append(chunk)
        selected_words.append(words)
        if is_short:
            short_count += 1

    return selected
