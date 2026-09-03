# ML PDF Evaluation Set

`ml_pdf_eval_200.jsonl` is a 200-case evaluation set grounded in
`~/Desktop/ml.pdf` (42 PDF pages/slides).

Each JSONL record contains a student-style question, whether the PDF can
answer it, the expected answer, the PDF page numbers that should appear in
retrieved context, and the citations that should appear in the final answer.
The first JSONL line stores source provenance and split counts.

Splits are grouped by concept: no topic's question variants appear in more
than one split. Use `train` to tune prompts, chunking, and retrieval settings;
use `val` to choose between approaches; keep `test` untouched until final
comparison.

For every answerable case, score retrieval with whether one of
`supporting_pages` appears in the retrieved chunks. Score final answers for
correctness, groundedness, and whether every returned citation matches an
entry in `expected_citations`. For unanswerable cases, score whether the
system declines to answer rather than inventing unsupported material.

Regenerate the JSONL after changing the source labels with:

```sh
environment/.venv/bin/python evaluation/build_ml_pdf_eval.py
```
