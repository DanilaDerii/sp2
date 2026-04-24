"""Student-side request and response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for a student chat query."""

    pack_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunkResponse(BaseModel):
    """One retrieved chunk included in the chat response."""

    chunk_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: str | None = None
    section: str | None = None
    topic: str | None = None
    distance: float | None = None


class ChatResponseBody(BaseModel):
    """Response body for a student chat query."""

    pack_id: str
    question: str
    answer: str
    used_debug_fallback: bool
    retrieved_chunks: list[RetrievedChunkResponse]
