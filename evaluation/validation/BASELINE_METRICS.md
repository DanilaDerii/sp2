# Validation Baseline Metrics

Configuration: current vector retriever, Nomic embedding model,
`top_k=5`, and raw vector candidate pool `k=20`.

| Validation PDF | Answerable questions | Recall@5 | Raw vector Recall@20 | MRR | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Machine Learning | 156 | 96.15% | 100.00% | 0.810 | 0.848 |
| Capital Budgeting | 200 | 69.50% | 99.50% | 0.422 | 0.490 |
| OS Memory Management | 200 | 75.50% | 100.00% | 0.475 | 0.544 |
| **Combined** | **556** | **79.14%** | **99.82%** | **0.550** | **0.610** |

Interpretation: almost every labeled page appears in the raw vector candidate
pool, but too many are demoted or removed before the final five chunks. The
next validation-only experiments should focus on final ranking and selection:
hybrid retrieval, reranking, chunk selection, and relevance thresholds.

The unseen same-domain and cross-domain test PDFs have not been built,
imported, or evaluated.
