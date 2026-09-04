"""Build page-grounded 200-question evaluation drafts for the non-ML PDFs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[1]
EVALUATION_ROOT = REPO_ROOT / "evaluation"
OUTPUT_DIR = EVALUATION_ROOT / "datasets"
MANIFEST_PATH = EVALUATION_ROOT / "document_split_manifest.json"

DOCUMENTS = (
    ("validation", EVALUATION_ROOT / "validation" / "Ch 4_ BBA1005_Using capital budgeting to assess feasibility of a business project SV.pdf"),
    ("validation", EVALUATION_ROOT / "validation" / "OS-Lecture-09.pdf"),
    ("test_same_domain", EVALUATION_ROOT / "test_same-domain" / "04 - NLP.pdf"),
    ("test_same_domain", EVALUATION_ROOT / "test_same-domain" / "Ch 7_BBA1005_ Bank Financial Instruments and Interest SV.pdf"),
    ("test_same_domain", EVALUATION_ROOT / "test_same-domain" / "OS-Lecture-07 (1).pdf"),
    ("test_cross_domain", EVALUATION_ROOT / "test_cross-domain" / "04 Learning to Define and Explore.pdf"),
    ("test_cross_domain", EVALUATION_ROOT / "test_cross-domain" / "Class#6-7 SDLC_SE_Agile.pdf"),
    ("test_cross_domain", EVALUATION_ROOT / "test_cross-domain" / "music.pdf"),
)

QUESTION_TEMPLATES = (
    "What is {topic}?",
    "Can you explain {topic} in simple terms?",
    "I am revising for an exam. What should I remember about {topic}?",
    "How does this lecture describe {topic}?",
    "Give me a concise answer about {topic} based on the course material.",
    "What is the main idea of {topic} in this document?",
    "Please summarize what the material says about {topic}.",
    "A classmate asked me about {topic}. How should I answer from this document?",
    "What does the course material teach about {topic}?",
    "What would be a correct short answer about {topic}?",
    "What details should I cite when explaining {topic}?",
    "Which concepts are important for understanding {topic}?",
    "Help me study the material related to {topic}.",
    "What does this page contribute to an explanation of {topic}?",
    "How would you describe {topic} using only this course material?",
    "What should a student not miss when learning about {topic}?",
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _pdf_pages(path: Path) -> list[str]:
    completed = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.split("\f")


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _heading(page_text: str) -> str:
    for line in page_text.splitlines():
        candidate = _normalize(line)
        letters = sum(character.isalpha() for character in candidate)
        if letters >= 5 and len(candidate) <= 160 and not candidate.isdigit():
            return candidate
    return _normalize(page_text)[:160]


def _content_pages(pages: list[str]) -> list[tuple[int, str, str]]:
    candidates: list[tuple[int, str, str]] = []
    for number, raw_text in enumerate(pages, start=1):
        text = _normalize(raw_text)
        word_count = len(text.split())
        if 10 <= word_count <= 450 and sum(character.isalpha() for character in text) >= 40:
            candidates.append((number, _heading(raw_text), text))
    if not candidates:
        raise ValueError("Need at least one text-bearing page")

    selected: list[tuple[int, str, str]] = []
    target_page_count = min(25, len(candidates))
    for position in range(target_page_count):
        index = round(position * (len(candidates) - 1) / (target_page_count - 1)) if target_page_count > 1 else 0
        candidate = candidates[index]
        if candidate not in selected:
            selected.append(candidate)
    for candidate in candidates:
        if len(selected) == target_page_count:
            break
        if candidate not in selected:
            selected.append(candidate)
    return selected


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_dataset(role: str, path: Path) -> dict[str, object]:
    slug = _slug(path.stem)
    samples: list[dict[str, object]] = []
    pages = _content_pages(_pdf_pages(path))
    for question_number in range(200):
        page_number, topic, answer = pages[question_number % len(pages)]
        topic_id = f"page-{page_number:03d}"
        template = QUESTION_TEMPLATES[(question_number // len(pages)) % len(QUESTION_TEMPLATES)]
        samples.append(
            {
                "id": f"{slug}-{topic_id}-{question_number + 1:03d}",
                "document_role": role,
                "answerable": True,
                "question": template.format(topic=topic),
                "expected_answer": answer,
                "supporting_pages": [page_number],
                "expected_citations": [f"{path.name} p. {page_number}"],
                "topic_group": topic_id,
                "label_quality": "generated_page_grounded_draft",
            }
        )
    if len(samples) != 200:
        raise ValueError(f"Expected 200 samples for {path.name}, found {len(samples)}")

    output_path = OUTPUT_DIR / f"{slug}_eval_200.jsonl"
    metadata = {
        "dataset": f"{slug}_eval_200",
        "source_pdf": str(path),
        "source_sha256": _file_hash(path),
        "document_role": role,
        "sample_count": len(samples),
        "label_quality": "generated_page_grounded_draft",
    }
    with output_path.open("w", encoding="utf-8") as output:
        output.write(json.dumps({"_metadata": metadata}, ensure_ascii=True) + "\n")
        for sample in samples:
            output.write(json.dumps(sample, ensure_ascii=True) + "\n")
    return {"role": role, "source_pdf": str(path), "dataset": str(output_path), "sample_count": len(samples)}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    for role, path in DOCUMENTS:
        if not path.is_file():
            raise FileNotFoundError(f"Evaluation PDF not found: {path}")
        records.append(_build_dataset(role, path))
    MANIFEST_PATH.write_text(json.dumps({"documents": records}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} datasets and {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
