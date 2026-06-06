# SP2 Teacher Builder

Local teacher-side backend for building portable course packs from source PDFs.

## Installation Guide

Run these commands first to prepare the teacher-side tooling.

### 1. Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Check that Ollama is available:

```bash
ollama --version
```

If the installer did not already start the service, start it manually:

```bash
ollama serve
```

On Linux, the installer often starts Ollama through systemd. If `ollama serve`
prints `address already in use`, Ollama is already running.

### 2. Install The Embedding Model

```bash
ollama pull all-minilm:latest
```

Verify that the model is installed and the local API is reachable:

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

The API response should include `all-minilm:latest` with embedding capability.

### 3. Install Teacher Python Dependencies

Run these commands from the `teacher/` directory:

```bash
cd /home/d/sp2/teacher
python -m venv environment/.venv
source environment/.venv/bin/activate
pip install -r environment/requirements.txt
```

Teacher dependencies are intentionally separate from student dependencies because
Docling pulls heavier document-processing packages.

## Build A Pack

Run this from the `teacher/` directory:

```bash
environment/.venv/bin/python -m backend.pipeline_runner "/path/to/course.pdf"
```

Example:

```bash
environment/.venv/bin/python -m backend.pipeline_runner "/home/d/Downloads/Week02 - Unit Testing.pdf"
```

## What The Pipeline Does

Current v1 flow:

```text
PDF -> Docling extraction -> chunks -> all-minilm embeddings -> pack files -> zip
```

Generated pack contents:

```text
pack.json
chunks.json
vectors.npy
```

The pack does not include the original PDF.

## Output Location

The runner derives the pack id and title from the PDF filename. For example:

```text
Week02 - Unit Testing.pdf -> week02---unit-testing
```

Generated outputs are written under the repo root:

```text
/home/d/sp2/artifacts/{pack_id}_pack/
/home/d/sp2/artifacts/{pack_id}.zip
```

If the same pack id is built again, the previous generated directory and zip are
replaced.

## Expected Output

A successful run prints a summary like:

```text
Teacher pipeline completed
source: /path/to/course.pdf
pack_id: week02---unit-testing
title: Week02 - Unit Testing
pages: 28
chunks: 28
embedding_model: all-minilm:latest
embedding_dim: 384
pack_dir: /home/d/sp2/artifacts/week02---unit-testing_pack
zip_path: /home/d/sp2/artifacts/week02---unit-testing.zip
```

## API Shell

The FastAPI app is currently only a shell with a health endpoint. Run it from
the `teacher/` directory:

```bash
environment/.venv/bin/uvicorn backend.app:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Notes

The first Docling run may download OCR/model files and can take longer. CPU-only
machines are supported, but PDF extraction can be slow.

The pack contract is documented in the root `project_log/` files and the root
`data_schema.txt`.
