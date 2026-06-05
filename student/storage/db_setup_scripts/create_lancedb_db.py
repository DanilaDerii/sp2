"""Create the student LanceDB database."""

from pathlib import Path


STORAGE_DIR = Path(__file__).resolve().parent.parent
LANCE_DIR = STORAGE_DIR / "lance_storage"
PACK_CHUNKS_TABLE_NAME = "pack_chunks"
DEFAULT_VECTOR_DIM = 384


def pack_chunks_schema(vector_dim: int = DEFAULT_VECTOR_DIM):
    try:
        import pyarrow as pa
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PyArrow is not installed in this Python environment. "
            "Install pyarrow before running this script."
        ) from exc

    return pa.schema(
        [
            pa.field("chunk_id", pa.string()),
            pa.field("installed_pack_id", pa.int64()),
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


def create_lancedb_db(vector_dim: int = DEFAULT_VECTOR_DIM) -> None:
    try:
        import lancedb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "LanceDB is not installed in this Python environment. "
            "Install lancedb and pyarrow before running this script."
        ) from exc

    LANCE_DIR.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(LANCE_DIR)

    if PACK_CHUNKS_TABLE_NAME not in db.list_tables():
        db.create_table(
            PACK_CHUNKS_TABLE_NAME,
            schema=pack_chunks_schema(vector_dim),
        )

    print(f"LanceDB database created at: {LANCE_DIR}")
    print(f"LanceDB table ready: {PACK_CHUNKS_TABLE_NAME}")


if __name__ == "__main__":
    create_lancedb_db()
