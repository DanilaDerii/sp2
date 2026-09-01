# Mini Retrieval — Numbered Pseudocode

## Testing scope

This is a reduced executable model of SP2 student retrieval. It preserves the
core behavior needed for structural, domain, mutation, data-flow, and integration
testing. It is not a replacement for the production retrieval modules.

### Inputs

- `installedPackId`: local SQLite identifier of one installed course pack
- `question`: student question to search for
- `topK`: optional maximum number of nearest candidates
- `maxDistance`: optional maximum accepted L2 distance
- `embedder`: external embedding provider treated as a black box

### Output

- `CourseContextPacket` containing:
  - mode: `course_context` or `no_course_context`
  - installed pack ID, logical pack ID, and embedding model
  - zero or more retrieved chunks
  - source metadata, distance, and score for every returned chunk
  - a short result message

### Modified state

- None. Retrieval reads SQLite and LanceDB but does not modify either store.

### Black-box operations

- `findInstalledPack(installedPackId)`
- `embedder.embed(texts, model)`
- `lanceSearch(queryVector, installedPackFilter, candidateLimit)`

## Main function

```text
FUNCTION miniRetrieveCourseContext(
    installedPackId,
    question,
    topK,
    maxDistance,
    embedder
):

01  IF installedPackId is boolean
        OR installedPackId is not a positive integer:
02      RETURN ERROR_INVALID_PACK_ID

03  normalizedQuestion = collapseWhitespace(question)

04  IF normalizedQuestion is empty:
05      RETURN ERROR_EMPTY_QUESTION

06  installedPack = findInstalledPack(installedPackId)

07  IF installedPack does not exist:
08      RETURN ERROR_PACK_NOT_FOUND

09  IF installedPack.isActive is false:
10      RETURN ERROR_PACK_INACTIVE

11  IF installedPack.embeddingModel != SUPPORTED_EMBEDDING_MODEL:
12      RETURN ERROR_EMBEDDING_MODEL_MISMATCH

13  IF topK was supplied:
14      resolvedTopK = topK
15  ELSE IF installedPack.defaultTopK is positive:
16      resolvedTopK = installedPack.defaultTopK
17  ELSE:
18      resolvedTopK = DEFAULT_TOP_K

19  IF resolvedTopK is boolean OR resolvedTopK <= 0:
20      RETURN ERROR_INVALID_TOP_K

21  IF maxDistance was supplied:
22      resolvedMaxDistance = maxDistance
23  ELSE:
24      resolvedMaxDistance = DEFAULT_MAX_DISTANCE

25  IF resolvedMaxDistance < 0:
26      RETURN ERROR_INVALID_MAX_DISTANCE

27  queryInput = "search_query: " + normalizedQuestion

28  vectors = embedder.embed(
        [queryInput],
        model = installedPack.embeddingModel
    )

29  IF number of vectors != 1:
30      RETURN ERROR_QUERY_VECTOR_COUNT

31  queryVector = []
32  FOR each value IN vectors[0]:
33      IF value is not numeric:
34          RETURN ERROR_NON_NUMERIC_QUERY_VECTOR
35      queryVector.append(float(value))

36  IF queryVector is empty
        OR length(queryVector) != installedPack.embeddingDimension:
37      RETURN ERROR_QUERY_VECTOR_DIMENSION

38  candidateRows = lanceSearch(
        queryVector,
        filter = installedPackId equals installedPack.id,
        candidateLimit = resolvedTopK
    )

39  retrievedChunks = []

40  FOR each row IN candidateRows:
41      distance = float(row.distance) if row.distance exists ELSE null

42      IF distance is null OR distance < 0:
43          score = null
44      ELSE:
45          score = 1 / (1 + distance)

46      IF distance is null OR distance > resolvedMaxDistance:
47          CONTINUE

48      retrievedChunks.append(
            RetrievedChunk(
                chunkId = row.chunkId,
                installedPackId = row.installedPackId,
                packId = row.packId,
                sourceId = row.sourceId,
                sourceType = row.sourceType,
                sourceTitle = row.sourceTitle,
                text = row.text,
                chunkIndex = row.chunkIndex,
                page = row.page,
                section = row.section,
                distance = distance,
                score = score
            )
        )

49  IF retrievedChunks is not empty:
50      RETURN CourseContextPacket(
            mode = "course_context",
            installedPackId = installedPack.id,
            packId = installedPack.packId,
            embeddingModel = installedPack.embeddingModel,
            chunks = retrievedChunks,
            message = "Found " + length(retrievedChunks)
                      + " relevant course-pack chunk(s)."
        )

51  RETURN CourseContextPacket(
        mode = "no_course_context",
        installedPackId = installedPack.id,
        packId = installedPack.packId,
        embeddingModel = installedPack.embeddingModel,
        chunks = [],
        message = "No relevant course-pack chunks found."
    )
```

`resolvedTopK` limits the LanceDB candidate search before distance filtering.
Consequently, the returned packet can contain fewer than `resolvedTopK` chunks.

## Graph-oriented pseudocode

This condensed version preserves the predicates, loops, definitions, and uses
that should become nodes in the CFG and data-flow graph. SQLite lookup, external
embedding, and LanceDB nearest-neighbor search remain black-box operations.

```text
FUNCTION miniRetrieveForTesting(
    installedPackId,
    question,
    topK,
    maxDistance,
    embedder
):

01  Validate installedPackId and normalize question

02  IF installedPackId or question is invalid:
03      RETURN ERROR_INVALID_INPUT

04  installedPack = findInstalledPack(installedPackId)

05  IF installedPack is missing or inactive:
06      RETURN ERROR_UNAVAILABLE_PACK

07  IF installedPack embedding model is unsupported:
08      RETURN ERROR_EMBEDDING_MODEL_MISMATCH

09  resolvedTopK = supplied topK or pack/default topK
10  resolvedMaxDistance = supplied maxDistance or default distance

11  IF resolvedTopK <= 0 OR resolvedMaxDistance < 0:
12      RETURN ERROR_INVALID_SEARCH_DOMAIN

13  queryInput = "search_query: " + normalizedQuestion
14  vectors = embedder.embed([queryInput], installedPack.embeddingModel)

15  IF vector count, numeric values, or dimension are invalid:
16      RETURN ERROR_INVALID_QUERY_VECTOR

17  queryVector = vectors[0]

18  candidateRows = lanceSearch(
        queryVector,
        installedPack.id filter,
        resolvedTopK limit
    )

19  retrievedChunks = []

20  FOR each row IN candidateRows:
21      distance = row.distance
22      score = null if distance is null or negative
                    else 1 / (1 + distance)

23      IF distance is null OR distance > resolvedMaxDistance:
24          CONTINUE

25      retrievedChunks.append(row metadata, text, distance, score)

26  IF retrievedChunks is not empty:
27      RETURN COURSE_CONTEXT_PACKET

28  RETURN NO_COURSE_CONTEXT_PACKET
```

## Deliberately excluded behavior

- MCP and HTTP transport
- Language-model answer generation
- Pack installation, deletion, or other writes
- Automatic embedding-model download or switching
- Detailed embedding-provider transport errors
- Candidate deduplication or reranking; `chunk_selector.py` currently contains
  design intent but no executable selection algorithm
- Searching multiple installed packs in one request

## Candidate testing points

- Positive-integer `installedPackId` domain, including Python boolean values
- Empty and whitespace-only questions
- Missing and inactive installed packs
- Installed-pack/query embedding-model equality
- Default, boundary, and invalid `topK` values
- Negative, zero, equal-boundary, and above-boundary distances
- Required `search_query:` embedding prefix
- Exactly one numeric query vector
- Query-vector dimension equality with installed-pack metadata
- LanceDB prefilter by installed-pack ID
- Candidate limiting before distance filtering
- Distance-to-score calculation: `1 / (1 + distance)`
- Preservation of source, page, section, distance, and score fields
- `course_context` versus `no_course_context` return branch
- Verification that SQLite and LanceDB remain unchanged
