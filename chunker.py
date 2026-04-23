import uuid

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def chunk_pages(
    pages: list[dict],
    source_id: str,
    source_type: str,
    source_title: str,
) -> list[dict]:
    chunks = []
    chunk_index = 0

    for page in pages:
        page_no = page["page"]
        text = page["text"].strip()

        if not text:
            continue

        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "source_id": source_id,
                    "source_type": source_type,
                    "source_title": source_title,
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "page": page_no,
                    "section": None,
                    "topic": None,
                    "char_count": len(chunk_text),
                })
                chunk_index += 1

            start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


if __name__ == "__main__":
    import json
    from pdf_parser import parse_pdf

    pages = parse_pdf("OS-Lecture-07.pdf")
    chunks = chunk_pages(
        pages,
        source_id="os-lecture-07",
        source_type="lecture",
        source_title="OS Lecture 07 - Deadlock",
    )

    print(f"Total chunks: {len(chunks)}")
    print(json.dumps(chunks[:3], indent=2))
