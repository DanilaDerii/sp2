import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from pdf_parser import parse_pdf
from chunker import chunk_pages
from embedder import embed_chunks, EMBEDDING_MODEL

BUILDER_VERSION = "0.1.0"
EMBEDDING_DIM = 384


def build_pack(
    pdf_path: str,
    source_id: str,
    source_type: str,
    source_title: str,
    pack_title: str,
    output_path: str,
    pack_id: str | None = None,
    description: str = "",
    version: str = "1.0.0",
    tutor_mode: str = "assistant",
    default_top_k: int = 5,
) -> str:
    print(f"Parsing {pdf_path}...")
    pages = parse_pdf(pdf_path)

    print("Chunking...")
    chunks = chunk_pages(pages, source_id, source_type, source_title)

    print("Embedding...")
    vectors = embed_chunks(chunks)

    pack = {
        "pack_id": pack_id or str(uuid.uuid4()),
        "title": pack_title,
        "version": version,
        "description": description,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dim": EMBEDDING_DIM,
        "tutor_mode": tutor_mode,
        "default_top_k": default_top_k,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "builder_version": BUILDER_VERSION,
    }

    tmp_dir = Path(output_path).parent / ".sp2build"
    tmp_dir.mkdir(exist_ok=True)

    pack_json = tmp_dir / "pack.json"
    chunks_json = tmp_dir / "chunks.json"
    vectors_npy = tmp_dir / "vectors.npy"

    pack_json.write_text(json.dumps(pack, indent=2))
    chunks_json.write_text(json.dumps(chunks, indent=2))
    np.save(str(vectors_npy), vectors)

    out = output_path if output_path.endswith(".sp2pack") else output_path + ".sp2pack"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(pack_json, "pack.json")
        zf.write(chunks_json, "chunks.json")
        zf.write(vectors_npy, "vectors.npy")

    import shutil
    shutil.rmtree(tmp_dir)

    print(f"Pack saved to {out}")
    print(f"  Chunks: {len(chunks)}")
    print(f"  Vectors: {vectors.shape}")
    return out


if __name__ == "__main__":
    build_pack(
        pdf_path="OS-Lecture-07.pdf",
        source_id="os-lecture-07",
        source_type="lecture",
        source_title="OS Lecture 07 - Deadlock",
        pack_title="Operating Systems - Lecture 07",
        output_path="os-lecture-07",
    )
