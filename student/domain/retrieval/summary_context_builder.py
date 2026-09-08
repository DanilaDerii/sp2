"""Build complete file or pack context for LM Studio summarization."""

from __future__ import annotations

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
    source_chunks = [
        chunk for chunk in pack_chunks if chunk.source_id == normalized_source_id
    ]
    if not source_chunks:
        available_sources = sorted({chunk.source_id for chunk in pack_chunks})
        available_text = ", ".join(available_sources) or "none"
        raise SummaryContextNotFoundError(
            f"Source not found in installed pack: {normalized_source_id}. "
            f"Available source_id values: {available_text}"
        )

    chunks = [_summary_chunk(chunk) for chunk in source_chunks]
    return SummaryContextPacket(
        mode="file_summary_context",
        installed_pack_id=installed_pack.id,
        pack_id=installed_pack.pack_id,
        pack_title=installed_pack.title,
        source_id=normalized_source_id,
        source_count=1,
        chunk_count=len(chunks),
        chunks=chunks,
        message=(
            f"Returned all {len(chunks)} chunk(s) from source "
            f"{normalized_source_id!r} for LM Studio to summarize."
        ),
    )


def build_pack_summary_context(
    *,
    installed_pack_id: int,
) -> SummaryContextPacket:
    """Return every ordered chunk from every source in an installed pack."""
    installed_pack = _get_active_installed_pack(installed_pack_id)
    pack_chunks = _ordered_pack_chunks(installed_pack.id)
    if not pack_chunks:
        raise SummaryContextNotFoundError(
            f"No chunks found for installed pack: {installed_pack.id}"
        )

    chunks = [_summary_chunk(chunk) for chunk in pack_chunks]
    source_count = len({chunk.source_id for chunk in pack_chunks})
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
            f"Returned all {len(chunks)} chunk(s) from {source_count} source file(s) "
            "for LM Studio to summarize."
        ),
    )
