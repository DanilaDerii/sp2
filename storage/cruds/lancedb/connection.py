"""LanceDB connection helpers for student retrieval storage."""

from pathlib import Path

from storage.database.setup.create_lancedb_db import (
    LANCE_DIR,
    PACK_CHUNKS_TABLE_NAME,
    create_lancedb_db,
)


def get_lancedb_connection(db_path: str | Path = LANCE_DIR):
    """Open the student LanceDB database directory."""
    import lancedb

    return lancedb.connect(Path(db_path).expanduser().resolve())


def get_pack_chunks_table(db_path: str | Path = LANCE_DIR):
    """Open the pack_chunks table, creating the LanceDB store if needed."""
    create_lancedb_db(verbose=False)
    db = get_lancedb_connection(db_path)
    return db.open_table(PACK_CHUNKS_TABLE_NAME)
