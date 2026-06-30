"""Build retrieval context packets for the future LM Studio tool layer."""

from __future__ import annotations

from student.storage.sqlite_cruds.pack_repository import InstalledPack, get_installed_pack

from .chunk_search import DEFAULT_TOP_K, search_chunks_for_query
from .models import CourseContextPacket, RetrievedChunk
from .query_embedder import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    DEFAULT_LM_STUDIO_BASE_URL,
    embed_question_for_pack,
)


class ContextBuilderError(RuntimeError):
    """Raised when a course context packet cannot be built."""


def _get_active_installed_pack(installed_pack_id: int) -> InstalledPack:
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise ContextBuilderError(f"Installed pack not found: {installed_pack_id}")
    if not installed_pack.is_active:
        raise ContextBuilderError(f"Installed pack is not active: {installed_pack_id}")
    return installed_pack


def _resolved_top_k(installed_pack: InstalledPack, top_k: int | None) -> int:
    if top_k is not None:
        return top_k
    return installed_pack.default_top_k or DEFAULT_TOP_K


def _course_context_message(chunks: list[RetrievedChunk]) -> str:
    return f"Found {len(chunks)} relevant course-pack chunk(s)."


def _no_course_context_message() -> str:
    return "No relevant course-pack chunks found."


def build_course_context_packet(
    *,
    installed_pack_id: int,
    question: str,
    top_k: int | None = None,
    max_distance: float | None = None,
    embedding_base_url: str = DEFAULT_LM_STUDIO_BASE_URL,
    embedding_timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
) -> CourseContextPacket:
    """Return course context or a no-context packet for one student question."""
    installed_pack = _get_active_installed_pack(installed_pack_id)
    query_embedding = embed_question_for_pack(
        question,
        installed_pack,
        base_url=embedding_base_url,
        timeout=embedding_timeout,
    )
    chunks = search_chunks_for_query(
        installed_pack_id=installed_pack.id,
        query_embedding=query_embedding,
        top_k=_resolved_top_k(installed_pack, top_k),
        max_distance=max_distance,
    )

    if chunks:
        return CourseContextPacket(
            mode="course_context",
            installed_pack_id=installed_pack.id,
            pack_id=installed_pack.pack_id,
            question=query_embedding.question,
            embedding_model=query_embedding.model,
            chunks=chunks,
            message=_course_context_message(chunks),
        )

    return CourseContextPacket(
        mode="no_course_context",
        installed_pack_id=installed_pack.id,
        pack_id=installed_pack.pack_id,
        question=query_embedding.question,
        embedding_model=query_embedding.model,
        chunks=[],
        message=_no_course_context_message(),
    )
