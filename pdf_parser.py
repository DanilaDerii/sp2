from docling.document_converter import DocumentConverter


def parse_pdf(path: str) -> list[dict]:
    converter = DocumentConverter()
    doc = converter.convert(path).document

    pages: dict[int, list[str]] = {}

    for element, _ in doc.iterate_items():
        if not hasattr(element, "prov") or not element.prov:
            continue
        if not hasattr(element, "text") or not element.text:
            continue

        page_no = element.prov[0].page_no
        pages.setdefault(page_no, []).append(element.text.strip())

    return [
        {"page": page_no, "text": "\n\n".join(texts)}
        for page_no, texts in sorted(pages.items())
    ]


if __name__ == "__main__":
    import sys
    import json

    path = sys.argv[1] if len(sys.argv) > 1 else "OS-Lecture-07.pdf"
    results = parse_pdf(path)
    print(json.dumps(results, indent=2))
