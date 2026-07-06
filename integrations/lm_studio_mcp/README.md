# SP2 LM Studio MCP Integration

Last audited: 2026-07-06

This directory contains the implemented MCP server that exposes SP2 teacher
ingest and student retrieval as local tools for LM Studio.

It lives at the project root because the same MCP server is the bridge for both
student retrieval tools and teacher ingestion tools.

The runtime boundary is:

```text
LM Studio chat UI
-> LM Studio MCP host/client
-> SP2 MCP stdio server
-> SP2 teacher FastAPI API and/or SP2 student FastAPI API
-> teacher pack build or SQLite/LanceDB retrieval
-> context packet back to LM Studio
```

LM Studio owns chat, model selection, and final answer generation. SP2 owns pack
import, query embedding calls/configuration, retrieval, and structured context
packets.

Current embedding direction: teacher pack creation and student query retrieval
use LM Studio's local OpenAI-compatible embeddings API with
`text-embedding-nomic-embed-text-v1.5`. MCP remains the tool boundary for
course-context calls.

## Tools

- `sp2_list_packs(pack_id=None, active_only=False)`
- `sp2_get_pack(installed_pack_id)`
- `sp2_get_course_context(pack, question)`
- `sp2_import_pack_from_path(pack_zip_path)`
- `sp2_ingest_pdf_from_path(pdf_path)`

## Local API Dependency

The student FastAPI server should be running before LM Studio calls student
runtime tools:

```bash
environment/.venv/bin/python -m uvicorn student.api:app --host 127.0.0.1 --port 8001
```

The teacher FastAPI server should be running before LM Studio calls teacher
ingest tools:

```bash
environment/.venv/bin/python -m uvicorn teacher.api:app --host 127.0.0.1 --port 8002
```

The MCP student tools call:

- `GET http://127.0.0.1:8001/packs`
- `GET http://127.0.0.1:8001/packs/{installed_pack_id}`
- `POST http://127.0.0.1:8001/retrieval/context`
- `POST http://127.0.0.1:8001/packs/import-path`

The MCP teacher ingest tool calls the teacher API, then imports the generated
zip through the student API:

- `POST http://127.0.0.1:8002/ingest/pdf-path`
- `POST http://127.0.0.1:8001/packs/import-path`

Its response is intentionally compact for LM Studio chat:

- `installed_pack_id`
- `pack`
- `pack_id`
- `title`
- `chunk_count`
- `zip_path`
- `message`

## LM Studio Configuration Shape

Use an absolute script path because LM Studio may launch the server outside the
repo working directory.

```json
{
  "mcpServers": {
    "sp2-course-context": {
      "command": "/home/d/sp2/environment/.venv/bin/python",
      "args": [
        "/home/d/sp2/integrations/lm_studio_mcp/server.py"
      ],
      "env": {
        "SP2_STUDENT_API_BASE_URL": "http://127.0.0.1:8001",
        "SP2_TEACHER_API_BASE_URL": "http://127.0.0.1:8002"
      }
    }
  }
}
```

## Implementation Notes

- Keep the MCP layer thin.
- Keep teacher and student business logic in their backend modules.
- Keep retrieval behavior in the student backend.
- Return structured context packets, not final prose answers.
- Avoid broad filesystem access from MCP tools.

Current file split:

- `server.py`: creates `FastMCP`, registers tool groups, and runs stdio.
- `student_tools.py`: student pack, import, and retrieval MCP tools.
- `teacher_tools.py`: teacher ingest MCP tools.
- `client.py`: shared HTTP helpers for student and teacher backend APIs.
- `validators.py`: MCP argument validation and small payload helpers.
