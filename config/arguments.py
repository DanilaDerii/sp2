"""Shared SP2 runtime arguments and defaults."""

from pathlib import Path


# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

# Chunking
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150
MAX_SECTION_LENGTH = 160

# Retrieval
DEFAULT_TOP_K = 5

# Embeddings
DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_HTTP_TIMEOUT = 120.0

# Teacher ingestion and pack export
SUPPORTED_SOURCE_SUFFIXES = (".pdf", ".odt", ".docx")
DEFAULT_BUILDER_VERSION = "v1-prototype"
REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")
