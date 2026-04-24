"""LanceDB bootstrap for the local course chunk table."""

from typing import Any

import lancedb
import pyarrow as pa

from backend.core.paths import LANCEDB_DIR, ensure_runtime_dirs


CHUNKS_TABLE_NAME = "course_chunks"


def _sql_quote(value: str) -> str:
    """Escape a string value for a simple LanceDB filter clause."""
    return value.replace("'", "''")


def chunk_table_schema(vector_dim: int) -> pa.Schema:
    """Return the v1 schema for the local course chunk table."""
    return pa.schema(
        [
            pa.field("chunk_id", pa.string()),
            pa.field("pack_id", pa.string()),
            pa.field("source_id", pa.string()),
            pa.field("source_type", pa.string()),
            pa.field("source_title", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), vector_dim)),
            pa.field("chunk_index", pa.int32()),
            pa.field("page", pa.string()),
            pa.field("section", pa.string()),
            pa.field("topic", pa.string()),
        ]
    )


def get_connection():
    """Open the local LanceDB root directory."""
    ensure_runtime_dirs()
    return lancedb.connect(LANCEDB_DIR)


def create_or_open_chunks_table(vector_dim: int):
    """Create the local chunk table if missing, otherwise open it."""
    db = get_connection()
    try:
        table = db.open_table(CHUNKS_TABLE_NAME)
        vector_field = table.schema.field("vector")
        existing_dim = vector_field.type.list_size
        if existing_dim != vector_dim:
            db.drop_table(CHUNKS_TABLE_NAME)
            return db.create_table(
                CHUNKS_TABLE_NAME,
                schema=chunk_table_schema(vector_dim),
            )
        return table
    except Exception:
        return db.create_table(
            CHUNKS_TABLE_NAME,
            schema=chunk_table_schema(vector_dim),
        )


# Chunk CRUD / retrieval helpers
def insert_chunks(records: list[dict[str, Any]], vector_dim: int):
    """Insert chunk rows into the local LanceDB table."""
    table = create_or_open_chunks_table(vector_dim)
    if records:
        table.add(records)
    return table


def list_chunks(pack_id: str) -> list[dict[str, Any]]:
    """List all chunk rows for one pack."""
    db = get_connection()
    table = db.open_table(CHUNKS_TABLE_NAME)
    return table.search().where(
        f"pack_id = '{_sql_quote(pack_id)}'"
    ).to_list()


def delete_chunks_for_pack(pack_id: str) -> None:
    """Delete all chunk rows belonging to one pack."""
    db = get_connection()
    table = db.open_table(CHUNKS_TABLE_NAME)
    table.delete(f"pack_id = '{_sql_quote(pack_id)}'")


def search_chunks(
    query_vector: list[float],
    pack_id: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return the nearest chunks for a query vector within one pack."""
    db = get_connection()
    table = db.open_table(CHUNKS_TABLE_NAME)
    return (
        table.search(query_vector)
        .where(f"pack_id = '{_sql_quote(pack_id)}'")
        .limit(limit)
        .to_list()
    )
