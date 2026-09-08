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

# Returned to LM Studio alongside retrieved chunks. Without it, small models
# pad answers with invented background detail and run long; measured on
# qwen3-4b-instruct this cut answers from 185 to 31 words and 32.5s to 6.9s
# while removing elaboration that was not in the course material.
COURSE_ANSWER_GUIDANCE = (
    "Answer using ONLY the course material in packet.chunks. Be concise: "
    "at most 120 words, prefer a short bulleted list. Cite page numbers. "
    "Do not add background knowledge that is not in the chunks. If the "
    "chunks do not answer the question, say so plainly."
)

# Chunk selection
CHUNK_CANDIDATE_MULTIPLIER = 4  # over-fetch: candidate_limit = top_k * this
SHORT_CHUNK_WORD_THRESHOLD = 12  # <=12 normalized words counts as "short"
SHORT_CHUNK_RATIO = 0.5  # fraction of top_k that may be short chunks (floor 1)
DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # Jaccard threshold for near-duplicate text

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
# Chosen for tool-call reliability, which the MCP retrieval flow depends on:
# llama-3.2-3b emitted a quoted string for the integer pack argument in every
# trial, while this model got it right in every trial. The non-thinking
# variant is deliberate - the thinking variant answers just as well but spends
# 260-352 words of hidden reasoning per response, making it 3-7x slower here.
DEFAULT_LLM_MODEL = "qwen3-4b-instruct-2507"
DEFAULT_LLM_MODEL_KEY = DEFAULT_LLM_MODEL
DEFAULT_LLM_MODEL_DOWNLOAD = (
    "https://huggingface.co/"
    "lmstudio-community/Qwen3-4B-Instruct-2507-GGUF@q4_k_m"
)

# Teacher ingestion and pack export
DEFAULT_BUILDER_VERSION = "v1-prototype"
REQUIRED_PACK_FILES = ("pack.json", "chunks.json", "vectors.npy")
