"""Standalone reduced SP2 retrieval model for software testing.

The normal SP2 setup/cleanup script is expected to initialize SQLite and LanceDB.
"""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
SQLITE_DB_PATH = REPO_ROOT / "storage" / "database" / "sqlite_storage" / "student_app.db"
LANCE_DB_PATH = REPO_ROOT / "storage" / "database" / "lance_storage"

SUPPORTED_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_TOP_K = 5
DEFAULT_MAX_DISTANCE = 1.0

Embedder = Callable[..., list[list[float]]]
ContextMode = Literal["course_context", "no_course_context"]


@dataclass(frozen=True, slots=True)
class MiniInstalledPack:
    installed_pack_id: int
    pack_id: str
    embedding_model: str
    embedding_dimension: int
    default_top_k: int
    is_active: bool


@dataclass(frozen=True, slots=True)
class MiniRetrievedChunk:
    chunk_id: str
    installed_pack_id: int
    pack_id: str
    source_id: str
    source_type: str
    source_title: str
    text: str
    chunk_index: int
    page: int | None
    section: str | None
    distance: float | None
    score: float | None


@dataclass(frozen=True, slots=True)
class MiniCourseContextPacket:
    mode: ContextMode
    installed_pack_id: int
    pack_id: str
    embedding_model: str
    chunks: list[MiniRetrievedChunk]
    message: str


def _find_installed_pack(installed_pack_id: int) -> MiniInstalledPack | None:
    """Read one installed-pack record from the real SP2 SQLite store."""
    connection = sqlite3.connect(SQLITE_DB_PATH)

    try:
        connection.row_factory = sqlite3.Row

        query = """
        SELECT id, pack_id, embedding_model, embedding_dim,
               default_top_k, is_active
        FROM installed_packs
        WHERE id = :installed_pack_id
        """
        parameters = {"installed_pack_id": installed_pack_id}

        cursor = connection.execute(query, parameters)
        row = cursor.fetchone()
    finally:
        connection.close()

    if row is None:
        return None
    return MiniInstalledPack(
        installed_pack_id=int(row["id"]),
        pack_id=row["pack_id"],
        embedding_model=row["embedding_model"],
        embedding_dimension=int(row["embedding_dim"]),
        default_top_k=int(row["default_top_k"]),
        is_active=bool(row["is_active"]),
    )


def _resolve_search_controls(
    installed_pack: MiniInstalledPack,
    top_k: int | None,
    max_distance: float | None,
) -> tuple[int, float]:
    """Resolve and validate the candidate limit and distance threshold."""
    resolved_top_k = top_k
    if resolved_top_k is None:
        resolved_top_k = installed_pack.default_top_k or DEFAULT_TOP_K
    if (
        isinstance(resolved_top_k, bool)
        or not isinstance(resolved_top_k, int)
        or resolved_top_k <= 0
    ):
        raise ValueError("top_k must be a positive integer")

    resolved_max_distance = max_distance
    if resolved_max_distance is None:
        resolved_max_distance = DEFAULT_MAX_DISTANCE
    if (
        isinstance(resolved_max_distance, bool)
        or not isinstance(resolved_max_distance, (int, float))
        or resolved_max_distance < 0
    ):
        raise ValueError("max_distance must be a non-negative number")
    return resolved_top_k, float(resolved_max_distance)


def _build_query_vector(
    normalized_question: str,
    installed_pack: MiniInstalledPack,
    embedder: Embedder,
) -> list[float]:
    """Embed one normalized question and validate its query vector."""
    query_input = f"search_query: {normalized_question}"
    vectors = embedder([query_input], model=installed_pack.embedding_model)
    if len(vectors) != 1:
        raise ValueError("embedder must return exactly one query vector")

    query_vector: list[float] = []
    for value in vectors[0]:
        try:
            query_vector.append(float(value))
        except (TypeError, ValueError) as error:
            raise ValueError("query vector must contain only numeric values") from error

    if (
        not query_vector
        or len(query_vector) != installed_pack.embedding_dimension
    ):
        raise ValueError("query vector dimension must match the installed pack")
    return query_vector


def _search_candidate_rows(
    query_vector: list[float],
    installed_pack_id: int,
    top_k: int,
) -> list[dict]:
    """Run pack-prefiltered L2 search and return at most top_k candidates."""
    import lancedb

    database = lancedb.connect(LANCE_DB_PATH)
    table = database.open_table("pack_chunks")
    pack_filter = f"installed_pack_id = {installed_pack_id}"

    vector_search = table.search(query_vector)
    pack_search = vector_search.where(pack_filter, prefilter=True)
    limited_search = pack_search.limit(top_k)
    candidate_rows = limited_search.to_list()
    return candidate_rows


def _collect_relevant_chunks(
    candidate_rows: list[dict],
    max_distance: float,
) -> list[MiniRetrievedChunk]:
    """Normalize LanceDB candidates and retain those within the distance limit."""
    relevant_chunks: list[MiniRetrievedChunk] = []
    for row in candidate_rows:
        raw_distance = row.get("_distance")
        if raw_distance is None:
            distance = None
        else:
            distance = float(raw_distance)

        if distance is None or distance < 0:
            score = None
        else:
            score = 1.0 / (1.0 + distance)

        page = row.get("page")
        section = row.get("section")
        chunk = MiniRetrievedChunk(
            chunk_id=row["chunk_id"],
            installed_pack_id=int(row["installed_pack_id"]),
            pack_id=row["pack_id"],
            source_id=row["source_id"],
            source_type=row["source_type"],
            source_title=row["source_title"],
            text=row["text"],
            chunk_index=int(row["chunk_index"]),
            page=int(page) if page is not None else None,
            section=str(section) if section is not None else None,
            distance=distance,
            score=score,
        )

        if chunk.distance is not None and chunk.distance <= max_distance:
            relevant_chunks.append(chunk)
    return relevant_chunks


def mini_retrieve_course_context(
    *,
    installed_pack_id: int,
    question: str,
    embedder: Embedder,
    top_k: int | None = None,
    max_distance: float | None = None,
) -> MiniCourseContextPacket:
    """Embed one question and return relevant chunks from one installed pack."""
    if (
        isinstance(installed_pack_id, bool)
        or not isinstance(installed_pack_id, int)
        or installed_pack_id <= 0
    ):
        raise ValueError("installed_pack_id must be a positive integer")

    normalized_question = " ".join(question.split()).strip()
    if not normalized_question:
        raise ValueError("question must not be empty")

    installed_pack = _find_installed_pack(installed_pack_id)
    if installed_pack is None:
        raise LookupError(f"installed pack not found: {installed_pack_id}")
    if not installed_pack.is_active:
        raise ValueError(f"installed pack is not active: {installed_pack_id}")
    if installed_pack.embedding_model != SUPPORTED_EMBEDDING_MODEL:
        raise ValueError("installed pack uses an unsupported embedding model")

    resolved_top_k, resolved_max_distance = _resolve_search_controls(
        installed_pack,
        top_k,
        max_distance,
    )
    query_vector = _build_query_vector(
        normalized_question,
        installed_pack,
        embedder,
    )
    candidate_rows = _search_candidate_rows(
        query_vector,
        installed_pack.installed_pack_id,
        resolved_top_k,
    )
    retrieved_chunks = _collect_relevant_chunks(
        candidate_rows,
        resolved_max_distance,
    )

    if retrieved_chunks:
        return MiniCourseContextPacket(
            mode="course_context",
            installed_pack_id=installed_pack.installed_pack_id,
            pack_id=installed_pack.pack_id,
            embedding_model=installed_pack.embedding_model,
            chunks=retrieved_chunks,
            message=f"Found {len(retrieved_chunks)} relevant course-pack chunk(s).",
        )

    return MiniCourseContextPacket(
        mode="no_course_context",
        installed_pack_id=installed_pack.installed_pack_id,
        pack_id=installed_pack.pack_id,
        embedding_model=installed_pack.embedding_model,
        chunks=[],
        message="No relevant course-pack chunks found.",
    )
