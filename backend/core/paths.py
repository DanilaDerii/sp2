"""Filesystem paths for local backend runtime data."""

from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
SQLITE_DIR = DATA_DIR / "sqlite"
LANCEDB_DIR = DATA_DIR / "lancedb"
PACKS_DIR = DATA_DIR / "packs"
TMP_DIR = DATA_DIR / "tmp"
SQLITE_DB_PATH = SQLITE_DIR / "app.db"


def ensure_runtime_dirs() -> None:
    """Create the local runtime data directories if they do not exist."""
    for path in (DATA_DIR, SQLITE_DIR, LANCEDB_DIR, PACKS_DIR, TMP_DIR):
        path.mkdir(parents=True, exist_ok=True)
