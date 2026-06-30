# SP2

SP2 is a local-first course-pack system for LM Studio.

LM Studio owns the chat UI, model loading, and final answer generation. SP2 owns
teacher pack creation, student pack import, local storage, retrieval, and the
MCP tool boundary that LM Studio can call.

## Runtime Shape

```text
Teacher workflow:
PDF -> text extraction -> chunks -> LM Studio embeddings -> pack zip

Student workflow:
pack zip -> SQLite/LanceDB import -> retrieval context -> LM Studio MCP tool
```

The current v1 pack contract is:

```text
pack.json
chunks.json
vectors.npy
```

## Setup

Paste this command in a terminal for the guided installer:

```bash
cd /home/d/sp2 && python3 installation/script.py
```

The script creates `environment/.venv`, installs requirements, initializes
SQLite/LanceDB storage, checks LM Studio embeddings when the local server is
running, starts and stops the backend once for a health check, then prints the
MCP JSON and backend start command.

Manual setup is:

```bash
cd /home/d/sp2
python -m venv environment/.venv
source environment/.venv/bin/activate
pip install -r environment/requirements.txt
```

SP2 currently uses LM Studio's local OpenAI-compatible embeddings API with:

```text
text-embedding-nomic-embed-text-v1.5
```

Start LM Studio's local server from the Developer tab, or run:

```bash
lms server start
```

Verify the model/API is available:

```bash
curl http://127.0.0.1:1234/v1/models
curl http://127.0.0.1:1234/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"text-embedding-nomic-embed-text-v1.5","input":"software testing"}'
```

The embedding response should contain a 768-value vector.

## Build A Teacher Pack

Run from the repo root:

```bash
environment/.venv/bin/python -m teacher.backend.pipeline_runner "/path/to/course.pdf"
```

Example:

```bash
environment/.venv/bin/python -m teacher.backend.pipeline_runner "/home/d/Downloads/Week01 - Basic Concepts and Preliminaries.pdf"
```

Generated outputs are written under:

```text
artifacts/{pack_id}_pack/
artifacts/{pack_id}.zip
```

## Import A Pack

Run from the repo root:

```bash
environment/.venv/bin/python -m student.storage.importer.pack_importer artifacts/{pack_id}.zip
```

## Run The Student API

Run from the repo root:

```bash
environment/.venv/bin/python -m uvicorn student.backend.app:app --host 127.0.0.1 --port 8001
```

Useful checks:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/packs
```

## LM Studio MCP Configuration

Use an absolute Python path because LM Studio may launch the MCP server outside
the repo working directory.

```json
{
  "mcpServers": {
    "sp2-course-context": {
      "command": "/home/d/sp2/environment/.venv/bin/python",
      "args": [
        "/home/d/sp2/student/integrations/lm_studio_mcp/server.py"
      ],
      "env": {
        "SP2_STUDENT_API_BASE_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

The student API must be running before LM Studio calls the MCP tool.

## Notes

Text-layer PDFs are extracted with the local `pdftotext` command when available.
Docling is not part of the default install because it pulls a heavy OCR/Torch
dependency stack. Install it into the same root venv only when scanned or complex
PDFs require the fallback path:

```bash
environment/.venv/bin/python -m pip install docling
```
