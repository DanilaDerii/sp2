"""Coordinate parsing a directory of files into one course pack.

This module will accept a path to a directory. The directory may contain files
directly and may also contain more directories inside it. The parser will search
the complete directory tree and find every supported source file.

The planned flow is:

1. Check that the supplied path exists and is a directory.
2. Recursively find supported files and sort them so builds are repeatable.
3. Select the existing extractor from each file's extension. PDF, ODT, and DOCX
   are currently supported. PPTX can be added later by registering its extractor.
4. Extract each file into the existing common ExtractedDocument model.
5. Give each document a source ID based on its path relative to the selected
   directory. This keeps files with the same name in different subdirectories
   separate without storing private absolute paths in the pack.
6. Split the extracted document into chunks with the existing common chunker.
7. Embed those chunks with the existing common embedder.
8. Append every file's embedded chunks to one combined list while preserving
   the order between chunk records and embedding vectors.
9. After every supported file has been processed, pass the combined list to the
   existing pack writer and zip exporter. They will create one pack.json, one
   chunks.json, one vectors.npy, and finally one pack zip.

Unsupported files should be ignored.

This module is only the coordinator. File-specific extraction, chunking,
embedding, pack writing, and zip creation remain in their existing modules.

check wether we have supported behavior to append to .json and .npy files new parsed
file data
"""
