"""Select useful, varied chunks from a larger semantic-search candidate set.

The current retrieval flow asks LanceDB for exactly the number of chunks that
must be returned to the language model. This can produce weak context when a
pack contains several similar cover pages, chapter outlines, or repeated
headings: those chunks are semantically related to a broad question, so they
can occupy every available result even though more useful explanatory chunks
exist slightly lower in the vector ranking. The intended solution is for
``chunk_search.py`` to retrieve a larger candidate set while preserving vector
distance, then pass those candidates through this module. This module should
remove exact or near-duplicate text, limit repeated low-information title
pages, preserve short chunks when they contain meaningful course information,
and return at most the caller's requested ``top_k`` chunks in relevance order.
It must not change stored vectors, database schemas, API or MCP contracts, and
it should avoid rules based only on text length because short slides such as an
objectives page may still be valuable. Any future selection rules should be
deterministic, independently testable, and conservative so that semantic
retrieval remains the main ranking signal rather than being replaced by a
collection of document-specific keyword rules.
"""
