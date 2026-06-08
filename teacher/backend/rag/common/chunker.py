"""Chunk generation worker for normalized extracted source text."""

from .models import ChunkedText, ExtractedDocument

DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150
MAX_SECTION_LENGTH = 160


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split plain text into overlapping character windows."""
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        if end < text_length:
            split_at = normalized.rfind(" ", start, end)
            if split_at > start:
                end = split_at

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break
        next_start = max(end - overlap, 0)
        if next_start > 0 and normalized[next_start - 1] != " ":
            next_space = normalized.find(" ", next_start)
            if next_space == -1:
                break
            next_start = next_space + 1

        start = next_start

    return chunks


def _infer_section_from_page_text(page_text: str) -> str | None:
    """Use the first meaningful page line as a simple section label."""
    for line in page_text.splitlines():
        section = " ".join(line.split()).strip()
        if section:
            return section[:MAX_SECTION_LENGTH]
    return None


def chunk_extracted_document(
    document: ExtractedDocument,
    *,
    source_id: str | None = None,
    source_type: str = "pdf",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkedText]:
    """Convert extracted page-like text into retrieval-ready chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("overlap must be 0 or greater")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    resolved_source_id = source_id or document.source_name
    chunks: list[ChunkedText] = []
    chunk_index = 0

    for page in document.pages:
        section = _infer_section_from_page_text(page.text)
        for chunk_text in _split_text(page.text, chunk_size, overlap):
            chunks.append(
                ChunkedText(
                    chunk_id=f"{resolved_source_id}::chunk::{chunk_index}",
                    source_id=resolved_source_id,
                    source_type=source_type,
                    source_title=document.source_name,
                    text=chunk_text,
                    chunk_index=chunk_index,
                    page=page.page_number,
                    section=section,
                    topic=None,
                    char_count=len(chunk_text),
                )
            )
            chunk_index += 1

    return chunks

