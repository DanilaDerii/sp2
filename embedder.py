import httpx
import numpy as np

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "all-minilm"
BATCH_SIZE = 32


def embed_chunks(chunks: list[dict]) -> np.ndarray:
    texts = [chunk["text"] for chunk in chunks]
    vectors = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = httpx.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": batch},
            timeout=60,
        )
        response.raise_for_status()
        vectors.extend(response.json()["embeddings"])
        print(f"Embedded {min(i + BATCH_SIZE, len(texts))}/{len(texts)} chunks")

    return np.array(vectors, dtype=np.float32)


if __name__ == "__main__":
    from pdf_parser import parse_pdf
    from chunker import chunk_pages

    pages = parse_pdf("OS-Lecture-07.pdf")
    chunks = chunk_pages(
        pages,
        source_id="os-lecture-07",
        source_type="lecture",
        source_title="OS Lecture 07 - Deadlock",
    )

    vectors = embed_chunks(chunks)
    print(f"Vectors shape: {vectors.shape}")
    np.save("vectors.npy", vectors)
    print("Saved vectors.npy")
