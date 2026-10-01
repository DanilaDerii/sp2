"""Build complete file or pack context for LM Studio summarization."""

from __future__ import annotations

from config.arguments import PACK_SUMMARY_CHUNKS_PER_SOURCE, SHORT_CHUNK_WORD_THRESHOLD
from storage.cruds.lancedb.chunk_repository import (
    PackChunk,
    list_chunks_for_installed_pack,
)
from storage.cruds.sqlite.pack_repository import InstalledPack, get_installed_pack

from .models import SummaryContextChunk, SummaryContextPacket


class SummaryContextError(RuntimeError):
    """Raised when summary context cannot be built."""


class SummaryContextNotFoundError(SummaryContextError):
    """Raised when a requested pack or source has no summary context."""


def _get_active_installed_pack(installed_pack_id: int) -> InstalledPack:
    installed_pack = get_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise SummaryContextNotFoundError(
            f"Installed pack not found: {installed_pack_id}"
        )
    if not installed_pack.is_active:
        raise SummaryContextError(
            f"Installed pack is not active: {installed_pack_id}"
        )
    return installed_pack


def _ordered_pack_chunks(installed_pack_id: int) -> list[PackChunk]:
    chunks = list_chunks_for_installed_pack(installed_pack_id)
    return sorted(
        chunks,
        key=lambda chunk: (
            chunk.source_id.casefold(),
            chunk.source_id,
            chunk.chunk_index,
            chunk.chunk_id,
        ),
    )


def _summary_chunk(chunk: PackChunk) -> SummaryContextChunk:
    return SummaryContextChunk(
        chunk_id=chunk.chunk_id,
        source_id=chunk.source_id,
        source_type=chunk.source_type,
        source_title=chunk.source_title,
        text=chunk.text,
        chunk_index=chunk.chunk_index,
        page=chunk.page,
        section=chunk.section,
    )


def _resolve_source_id(pack_chunks: list[PackChunk], source_id: str) -> str:
    """Resolve a requested source id without discarding its stored casing.

    Exact matches remain preferred so packs containing filenames that differ
    only by case or whitespace are still addressable. A case- and
    whitespace-insensitive request is accepted only when it identifies one
    stored source unambiguously.
    """
    available_sources = {chunk.source_id for chunk in pack_chunks}
    if source_id in available_sources:
        return source_id

    normalized_source_id = "".join(source_id.casefold().split())
    normalized_matches = sorted(
        stored_source_id
        for stored_source_id in available_sources
        if "".join(stored_source_id.casefold().split()) == normalized_source_id
    )
    if len(normalized_matches) == 1:
        return normalized_matches[0]
    if len(normalized_matches) > 1:
        matches_text = ", ".join(normalized_matches)
        raise SummaryContextError(
            f"Source reference is ambiguous: {source_id}. "
            f"Matching source_id values: {matches_text}"
        )

    available_text = ", ".join(sorted(available_sources)) or "none"
    raise SummaryContextNotFoundError(
        f"Source not found in installed pack: {source_id}. "
        f"Available source_id values: {available_text}"
    )


def build_file_summary_context(
    *,
    installed_pack_id: int,
    source_id: str,
) -> SummaryContextPacket:
    """Return every ordered chunk for one source file in an installed pack."""
    installed_pack = _get_active_installed_pack(installed_pack_id)
    normalized_source_id = source_id.strip()
    if not normalized_source_id:
        raise SummaryContextError("source_id must not be empty")

    pack_chunks = _ordered_pack_chunks(installed_pack.id)
    resolved_source_id = _resolve_source_id(pack_chunks, normalized_source_id)
    source_chunks = [
        chunk for chunk in pack_chunks if chunk.source_id == resolved_source_id
    ]

    chunks = [_summary_chunk(chunk) for chunk in source_chunks]
    return SummaryContextPacket(
        mode="file_summary_context",
        installed_pack_id=installed_pack.id,
        pack_id=installed_pack.pack_id,
        pack_title=installed_pack.title,
        source_id=resolved_source_id,
        source_count=1,
        chunk_count=len(chunks),
        chunks=chunks,
        message=(
            f"Returned all {len(chunks)} chunk(s) from source "
            f"{resolved_source_id!r} for LM Studio to summarize."
        ),
    )


def _opening_chunks(source_chunks: list[PackChunk]) -> list[PackChunk]:
    """Return the first substantive chunks of one source file.

    Title pages are skipped by size rather than position: in a PDF the first
    chunk is usually an 11-word title slide, but in a Word document it is the
    lecture introduction, which is the most useful chunk of all.
    """
    substantive = [
        chunk
        for chunk in source_chunks
        if len(chunk.text.split()) > SHORT_CHUNK_WORD_THRESHOLD
    ]
    return (substantive or source_chunks)[:PACK_SUMMARY_CHUNKS_PER_SOURCE]


def build_pack_summary_context(
    *,
    installed_pack_id: int,
) -> SummaryContextPacket:
    """Return an overview of an installed pack: the opening chunks of each source."""
    installed_pack = _get_active_installed_pack(installed_pack_id)
    pack_chunks = _ordered_pack_chunks(installed_pack.id)
    if not pack_chunks:
        raise SummaryContextNotFoundError(
            f"No chunks found for installed pack: {installed_pack.id}"
        )

    chunks_by_source: dict[str, list[PackChunk]] = {}
    for chunk in pack_chunks:
        chunks_by_source.setdefault(chunk.source_id, []).append(chunk)

    chunks = [
        _summary_chunk(chunk)
        for source_chunks in chunks_by_source.values()
        for chunk in _opening_chunks(source_chunks)
    ]
    source_count = len(chunks_by_source)
    source_list = ", ".join(chunks_by_source)
    return SummaryContextPacket(
        mode="pack_summary_context",
        installed_pack_id=installed_pack.id,
        pack_id=installed_pack.pack_id,
        pack_title=installed_pack.title,
        source_id=None,
        source_count=source_count,
        chunk_count=len(chunks),
        chunks=chunks,
        message=(
            f"Overview only: returned the opening {len(chunks)} of {len(pack_chunks)} "
            f"chunk(s) across {source_count} source file(s). For a specific question "
            "use sp2_get_course_context; for the full content of one file use "
            f"sp2_get_file_summary_context. Source files: {source_list}"
        ),
    )
