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

After importing `ml.pdf` into SP2 and starting the backend and LM Studio's
embedding server, evaluate held-out retrieval with:

```sh
environment/.venv/bin/python evaluation/run_retrieval_eval.py --pack-id PACK_ID --split test
```

The runner reports `retrieval_recall_at_k`: the share of answerable questions
for which a retrieved chunk includes at least one labeled PDF page. It also
reports `citation_ready_rate`, because the retrieval response carries each
chunk's source page. This verifies evidence availability, not whether the
chat model formats citations correctly in its final prose.
