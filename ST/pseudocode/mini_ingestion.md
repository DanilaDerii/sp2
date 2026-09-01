# Mini Ingestion — Numbered Pseudocode

## Testing scope

This is a reduced executable model of SP2 content ingestion. It preserves the
core behavior needed for structural, domain, mutation, and integration testing.
It is not a replacement for the production ingestion pipeline.

### Inputs

- `pdfPath`: local path to one PDF file
- `packId`: logical course-pack identifier
- `title`: course-pack title
- `version`: course-pack version
- `chunkSize`: maximum chunk size in characters
- `overlap`: character overlap between neighboring chunks
- `embedder`: external embedding provider treated as a black box

### Output

- `IngestionResult` containing the installed pack ID, pack ID, title, version,
  chunk count, embedding model, embedding dimension, ZIP path, and installation
  path

### Modified state

- ZIP artifact storage
- Installed-pack files
- SQLite installed-pack metadata
- LanceDB chunks and vectors

### Imported black-box operations

- `extractPdfPages(pdfPath)`
- `createOverlappingChunks(pages, chunkSize, overlap)`
- `embedder.embed(texts)`
- `writePack(metadata, chunks, vectors)`
- `validatePack(packDirectory)`
- `exportPackZip(packDirectory)`
- `installPackFiles(zipPath, installName)`
- SQLite and LanceDB repository operations

## Main function

```text
FUNCTION miniIngestPdf(
    pdfPath,
    packId,
    title,
    version,
    chunkSize,
    overlap,
    embedder
):

01  IF pdfPath is empty
        OR pdfPath does not exist
        OR pdfPath is not a file
        OR extension is not ".pdf":
02      RETURN ERROR_INVALID_PDF

03  IF packId is empty OR title is empty OR version is empty:
04      RETURN ERROR_INVALID_METADATA

05  IF chunkSize <= 0
        OR overlap < 0
        OR overlap >= chunkSize:
06      RETURN ERROR_INVALID_CHUNK_DOMAIN

07  installName = safeName(packId + "-" + version)

08  IF installed-pack files already contain installName
        OR SQLite already contains the same packId and version:
09      RETURN ERROR_DUPLICATE_PACK

10  pages = extractPdfPages(pdfPath)

11  IF pages is empty OR every extracted page is blank:
12      RETURN ERROR_EMPTY_SOURCE

13  chunks = createOverlappingChunks(pages, chunkSize, overlap)

14  IF chunks is empty:
15      RETURN ERROR_NO_CHUNKS

16  documentInputs = []
17  FOR each chunk IN chunks:
18      documentInputs.append("search_document: " + chunk.text)

19  vectors = embedder.embed(documentInputs)

20  IF number of vectors != number of chunks:
21      RETURN ERROR_VECTOR_COUNT

22  embeddingDimension = length of vectors[0]

23  IF embeddingDimension <= 0
        OR any vector has a different dimension:
24      RETURN ERROR_VECTOR_DIMENSION

25  metadata = buildMetadata(
        packId,
        title,
        version,
        embedder.modelName,
        embeddingDimension
    )

26  packDirectory = writePack(metadata, chunks, vectors)

27  IF validatePack(packDirectory) fails:
28      RETURN ERROR_INVALID_PACK

29  zipPath = exportPackZip(packDirectory)
30  installPath = installPackFiles(zipPath, installName)

31  installedPack = insertInstalledPackIntoSQLite(
        metadata,
        installPath
    )

32  insertedChunkCount = insertChunksAndVectorsIntoLanceDB(
        installedPack.id,
        metadata.packId,
        chunks,
        vectors
    )

33  IF insertedChunkCount != number of chunks:
34      RETURN ERROR_STORAGE_COUNT

35  RETURN IngestionResult(
        installedPackId = installedPack.id,
        packId = metadata.packId,
        title = metadata.title,
        version = metadata.version,
        chunkCount = insertedChunkCount,
        embeddingModel = metadata.embeddingModel,
        embeddingDimension = metadata.embeddingDimension,
        zipPath = zipPath,
        installPath = installPath
    )
```

## Graph-oriented pseudocode

This condensed version preserves the important predicates and data transformations.
Its numbered operations are intended to become nodes in the CFG and data-flow graph.
Pack installation is treated as one black-box operation that writes installed files,
SQLite metadata, and LanceDB chunk-vector rows.

```text
FUNCTION miniIngestPdfForTesting(
    pdfPath,
    packId,
    title,
    version,
    chunkSize,
    overlap,
    embedder
):

01  Validate PDF path, metadata, chunkSize, and overlap

02  IF any input is invalid:
03      RETURN ERROR_INVALID_INPUT

04  IF packId and version are already installed:
05      RETURN ERROR_DUPLICATE_PACK

06  pages = extractPdfPages(pdfPath)
07  chunks = createOverlappingChunks(pages, chunkSize, overlap)

08  IF chunks is empty:
09      RETURN ERROR_NO_CONTENT

10  documentInputs = []
11  FOR each chunk IN chunks:
12      documentInputs.append("search_document: " + chunk.text)

13  vectors = embedder.embed(documentInputs)

14  IF vector count or vector dimensions are invalid:
15      RETURN ERROR_INVALID_VECTORS

16  metadata = buildMetadata(
        packId,
        title,
        version,
        embedder.modelName,
        dimension of vectors
    )

17  packDirectory = writePack(metadata, chunks, vectors)

18  IF validatePack(packDirectory) fails:
19      RETURN ERROR_INVALID_PACK

20  zipPath = exportPackZip(packDirectory)
21  installedPack = installPack(zipPath)

22  RETURN IngestionResult(
        installedPackId = installedPack.id,
        packId = metadata.packId,
        title = metadata.title,
        version = metadata.version,
        chunkCount = number of chunks,
        embeddingModel = metadata.embeddingModel,
        embeddingDimension = metadata.embeddingDimension,
        zipPath = zipPath,
        installPath = installedPack.installPath
    )
```

## Deliberately excluded behavior

- MCP and FastAPI transport
- ODT, DOCX, PPTX, and directory ingestion
- Detailed embedding-provider transport errors
- Installation rollback
- Pack listing, deletion, and update behavior

## Candidate testing points

- Required-input and PDF-path domains
- `chunkSize` and `overlap` boundaries
- Empty extraction and empty chunks
- Duplicate pack detection
- Document embedding prefix
- Chunk/vector count equality
- Embedding-dimension consistency
- Required pack-file validation
- SQLite field values
- LanceDB row count and field values
- Returned installation result
