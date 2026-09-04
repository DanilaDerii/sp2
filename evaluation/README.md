# ML PDF Evaluation Set

`ml_pdf_eval_200.jsonl` is a 200-case evaluation set grounded in
`~/Desktop/ml.pdf` (42 PDF pages/slides).

Each JSONL record contains a student-style question, whether the PDF can
answer it, the expected answer, the PDF page numbers that should appear in
retrieved context, and the citations that should appear in the final answer.
The first JSONL line stores source provenance and split counts.

Splits are grouped by concept: no topic's question variants appear in more
than one split. The set has 160 validation and 40 held-out test cases. Use
validation to compare prompts, chunking, and retrieval settings; keep test
untouched until the final comparison. Add a train split only when learning
parameters from the questions, such as fine-tuning an embedding model or
training a reranker.

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

For a generated single-document dataset, evaluate all 200 records with:

```sh
environment/.venv/bin/python evaluation/run_retrieval_eval.py --pack-id PACK_ID --dataset DATASET_PATH --all-samples
```

The runner reports `Recall@5` for final context, raw vector `Recall@20` before
the chunk selector filters candidates, MRR for the first correct result's
rank, and nDCG@5 for the whole final ordering. It also reports
`citation_ready_rate`, because the retrieval response carries each chunk's
source page. This verifies evidence availability, not whether the chat model
formats citations correctly in its final prose.

Each evaluator run appends a compact, immutable record to
`ml_pdf_eval_progress.jsonl`. It captures the time, Git revision, pack ID,
split, `top_k`, embedding model, and metrics, so retrieval changes can be
compared over time. `--report` remains a replaceable detailed snapshot; use
`--no-history` for a diagnostic run that should not affect the progress log.

## Document-Level Evaluation

`document_split_manifest.json` defines whole-PDF roles: validation, unseen
same-domain test, and unseen cross-domain test. This protects against tuning
to the same document used for final evaluation.

`build_document_eval_sets.py` creates a 200-question page-grounded draft for
each non-ML PDF. It selects up to 25 text-bearing pages and distributes
student-style question variants across them. This accommodates short or
visual-heavy slide decks without inventing labels for pages with no extractable
evidence. These are useful for exercising the framework, but
are labeled `generated_page_grounded_draft` and need subject-matter review
before they support a production-quality claim.

```sh
environment/.venv/bin/python evaluation/build_document_eval_sets.py
```
