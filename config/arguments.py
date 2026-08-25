"""Shared SP2 runtime arguments and defaults."""

from pathlib import Path


# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

# Local services
DEFAULT_SP2_BACKEND_BASE_URL = "http://127.0.0.1:8001"
DEFAULT_MCP_SERVER_NAME = "lecture_sense_rag"

# Chunking
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 150
MAX_SECTION_LENGTH = 160

# Retrieval
DEFAULT_TOP_K = 5

# Embeddings
DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
DEFAULT_EMBEDDING_DIM = 768
DEFAULT_EMBEDDING_MODEL_KEY = DEFAULT_EMBEDDING_MODEL
DEFAULT_EMBEDDING_MODEL_DOWNLOAD = (
    "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF@q4_k_m"
)
DEFAULT_HTTP_TIMEOUT = 120.0

# Chat model
DEFAULT_LLM_MODEL = "qwen2.5-7b-instruct-1m"
DEFAULT_LLM_MODEL_KEY = DEFAULT_LLM_MODEL
DEFAULT_LLM_MODEL_DOWNLOAD = (
    "https://huggingface.co/"
    "lmstudio-community/Qwen2.5-7B-Instruct-1M-GGUF@q4_k_m"
)

# Chat model comparison harness (evaluation/) — candidate download URLs for
# models not already covered by DEFAULT_LLM_MODEL_DOWNLOAD above.
CANDIDATE_EVAL_MODELS: dict[str, str] = {
    "qwen2.5-3b-instruct": (
        "https://huggingface.co/"
        "lmstudio-community/Qwen2.5-3B-Instruct-GGUF@q4_k_m"
    ),
    "llama-3.2-3b-instruct": (
        "https://huggingface.co/"
        "lmstudio-community/Llama-3.2-3B-Instruct-GGUF@q4_k_m"
    ),
    # lmstudio-community's copy of this repo intermittently fails to resolve
    # through LM Studio's HF proxy ("Invalid username or password", not an
    # auth problem on our end - confirmed via `lms whoami`). bartowski's repo
    # has the same weights/quantization (lmstudio-community's own README
    # credits bartowski for the GGUF conversion) and resolves reliably.
    "phi-3.5-mini-instruct": (
        "https://huggingface.co/"
        "bartowski/Phi-3.5-mini-instruct-GGUF@q4_k_m"
    ),
}

# Teacher ingestion and pack export
DEFAULT_BUILDER_VERSION = "v1-prototype"
REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")
