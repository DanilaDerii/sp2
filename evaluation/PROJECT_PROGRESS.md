# Retrieval Evaluation Progress

This file is the human-readable timeline for the `ml.pdf` retrieval work.
Use `ml_pdf_eval_progress.jsonl` for append-only machine-readable run metrics.

## 2026-09-02: Retrieval Investigation

- Confirmed that the original retrieval flow embeds a student question, runs
  LanceDB vector search within one installed pack, and returns the best five
  chunks to LM Studio.
- Confirmed the chunk-selection change in `Updated_Branch`: it over-fetches
  four times the requested result count, removes near-duplicate text, and caps
  short chunks. This is a safety filter, not a semantic reranker.
- Found that the source chunker is page/slide-boundary based. It normalizes a
  page's text, then makes 1,200-character windows with 150-character overlap.
  It does not merge title-only slides with nearby explanatory slides.
- Identified the practical failure mode: a title or agenda slide is stored as
  a standalone retrieval chunk and can outrank useful explanatory content.

## 2026-09-03: Tool and Model Diagnosis

- Verified that `sp2_get_pack(installed_pack_id=1)` is correctly declared in
  the MCP schema and that the live backend returns pack 1.
- Determined that the observed failure happened before SP2 received a call:
  the smaller Llama 3.2 3B model did not generate a valid tool-call payload.
- Noted an MCP naming inconsistency that can make tool calling harder:
  `sp2_get_pack` uses `installed_pack_id`, while retrieval and deletion use
  `pack` for the same local identifier.

## 2026-09-03: Evaluation Dataset and Baseline

- Created `ml_pdf_eval_200.jsonl` from the 42-page `~/Desktop/ml.pdf` lecture.
- The dataset contains 195 answerable student-style questions with expected
  PDF pages and citations, plus 5 out-of-scope questions for abstention tests.
- Split by concept to avoid paraphrase leakage: 160 validation and 40 held-out
  test cases. A training split will be added only if we learn parameters from
  the question set, such as when training a reranker.
- Built and installed the local `ml` pack as installed pack ID 4. The baseline
  ingestion produced 42 chunks, effectively one chunk per PDF page.
- Ran the held-out test split with `top_k=5` and the Nomic embedding model.
  Results: `Recall@5 = 81.25%` (26 of 32 answerable cases), citation-ready
  rate `81.25%`, and out-of-scope no-context rate `0%`.
- The most frequent miss was the algorithm-choice page: generic introductory
  pages ranked above page 34. The 80/20 training/testing slide also missed
  because its limited text is weak semantic evidence.

## 2026-09-03: Progress Tracking

- Updated `run_retrieval_eval.py` to append a compact record for every run to
  `ml_pdf_eval_progress.jsonl`.
- Each progress record includes the timestamp, Git revision, installed pack,
  split, `top_k`, embedding model, and summary metrics.
- `ml_pdf_test_report.json` remains the detailed latest-run snapshot and is
  intentionally replaced when the same report path is used again.

## Current Goals

1. Keep the current test split frozen as the baseline. Use validation to
   develop and choose changes before another test run. Add training data only
   when a model or parameters are learned from the evaluation questions.
2. Add ranking diagnostics: `Recall@20`, MRR, and short/title-chunk rate.
   This will show whether failures come from weak candidate retrieval or poor
   ranking of candidates that were already found.
3. Improve ingestion for slides and PDFs: retain headings as context, merge or
   tag title-only/low-information slides, and split longer text at meaningful
   boundaries rather than only character limits.
4. Evaluate hybrid retrieval (semantic plus keyword search) and a second-stage
   reranker. Prefer the option that improves validation metrics without making
   title-page rate or latency unacceptable.
5. Tune the relevance threshold using validation questions so out-of-scope
   requests can return no context instead of unrelated course material.
6. Separately test final-answer quality: correctness, groundedness, citation
   formatting, and tool-call success. Retrieval page labels only prove that a
   citation is available; they do not prove the chat model cited it correctly.

## Active Retrieval To-Do List

1. Add miss-reason diagnostics. For every evaluation miss, determine whether
   the expected page was absent from the raw vector top 20, ranked below the
   final five, or removed by duplicate/short-chunk selection.
2. Audit 20-30 validation questions per PDF. Correct labels, add valid
   alternative supporting pages, and replace vague generated prompts with
   realistic student questions where needed.
3. Add a reranker over the top 20 vector candidates and compare it with the
   current retriever on the combined validation metrics and latency.
4. Compare hybrid retrieval, combining vector and keyword candidates before
   final ranking.
5. Add out-of-scope questions for every validation PDF and tune abstention
   thresholds independently from final ranking.
6. Choose and freeze the best validation configuration.
7. Run the frozen configuration once on unseen same-domain and cross-domain
   test PDFs. Do not use those results to continue tuning.

## 2026-09-04: Metric and Split Policy

- Resplit the 200 cases into 160 validation and 40 held-out test cases. There
  is no training split because the current system does not learn parameters
  from the question set.
- Added four retrieval metrics to the evaluator:
  - `Recall@5`: correct evidence appears in the final five context chunks.
  - Raw vector `Recall@20`: correct evidence appears in LanceDB's top 20
    candidates before the chunk selector filters them.
  - MRR: reciprocal rank of the first correct final chunk.
  - nDCG@5: quality of the complete final five-chunk ordering.
- Current validation baseline for pack 4: `Recall@5 = 96.15%`, raw vector
  `Recall@20 = 100%`, `MRR = 0.810`, and `nDCG@5 = 0.848`.
- Interpretation: the vector search finds all labeled evidence in its
  candidate pool, but final ranking/selection still drops or demotes some
  evidence. Prioritize reranking and selection experiments before replacing
  the embedding model.

## Selection Rule

1. Implement one candidate configuration at a time: current retriever, hybrid
   retrieval, hybrid plus reranker, different chunking, or threshold changes.
2. Run every candidate on the 160-case validation split and append the result
   to the progress log.
3. Choose and freeze the best validation configuration, considering quality,
   citation readiness, abstention behavior, and latency.
4. Run the 40-case test split once for the final unbiased result.

Do not repeatedly inspect test results and then change the algorithm. Doing
that turns the test set into another validation set and biases the final score.

## 2026-09-04: Multi-PDF Evaluation Expansion

- Organized evaluation by whole document rather than only question-level
  splits. The document manifest has two validation PDFs, three unseen
  same-domain test PDFs, and three unseen cross-domain test PDFs.
- Created eight additional 200-question page-grounded draft datasets, for
  1,600 new question-answer-citation records. Together with the ML dataset,
  the framework now covers nine PDFs and 1,800 labeled records.
- The additional labels are generated from extractable page text and marked
  `generated_page_grounded_draft`. They are suitable for exercising retrieval
  and the evaluation pipeline, but subject-matter review is required before
  using them to make a production-quality performance claim.
- Fresh-start note: ZIP artifacts were removed. Existing installed-pack
  directories remain local runtime state and were not deleted by this work.

## 2026-09-04: Multi-PDF Validation Baseline

- Built and imported the two additional validation packs: capital budgeting
  (pack 5, 77 chunks) and OS memory management (pack 6, 41 chunks). The ML
  validation pack remains pack 4.
- Ran validation only. No unseen same-domain or cross-domain test PDF has been
  built, imported, or evaluated.
- Combined across 556 answerable validation questions, the current retriever
  achieved `Recall@5 = 79.14%`, raw vector `Recall@20 = 99.82%`, `MRR =
  0.550`, and `nDCG@5 = 0.610`.
- The large gap between Recall@20 and Recall@5 confirms that candidate
  retrieval is not the main bottleneck. Rank/selection improvements should be
  evaluated on these same validation PDFs before one frozen configuration is
  tested on unseen documents.
