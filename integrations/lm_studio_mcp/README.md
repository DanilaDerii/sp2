# SP2 LM Studio MCP Integration

Last audited: 2026-08-15

This directory contains the implemented MCP server that exposes SP2 ingest,
pack management, retrieval, and summary context as local tools for LM Studio.

It lives at the project root because the same MCP server is the bridge for both
student retrieval tools and teacher ingestion tools.

The runtime boundary is:

```text
LM Studio chat UI
-> LM Studio MCP host/client
-> SP2 MCP stdio server
-> SP2 unified FastAPI backend
-> teacher pack build or SQLite/LanceDB retrieval
-> context packet back to LM Studio
```

LM Studio owns chat, model selection, and final answer generation. SP2 owns pack
import, query embedding calls/configuration, retrieval, and structured context
packets.

Current embedding direction: teacher pack creation and student query retrieval
use LM Studio's local OpenAI-compatible embeddings API with
`text-embedding-nomic-embed-text-v1.5`. MCP remains the tool boundary for
course-context and summary-context calls.

## Tools

- `sp2_list_packs(pack_id=None, active_only=False)`
- `sp2_get_pack(installed_pack_id)`
- `sp2_get_course_context(pack, question)`
- `sp2_get_file_summary_context(pack, source_id)`
- `sp2_get_pack_summary_context(pack)`
- `sp2_import_pack_from_path(pack_zip_path)`
- `sp2_delete_pack(pack)`
- `sp2_ingest_file_from_path(file_path)`

Current supported teacher source suffixes:

- `.pdf`
- `.odt`
- `.docx`
- `.pptx`

## Local Backend Dependency

The installer starts the SP2 backend automatically. For later starts on macOS
or Linux, run:

```bash
environment/.venv/bin/python -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

On Windows PowerShell, run:

```powershell
& '.\environment\.venv\Scripts\python.exe' -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

The MCP tools call:

- `GET http://127.0.0.1:8001/packs`
- `GET http://127.0.0.1:8001/packs/{installed_pack_id}`
- `POST http://127.0.0.1:8001/retrieval/context`
- `POST http://127.0.0.1:8001/summaries/file-context`
- `POST http://127.0.0.1:8001/summaries/pack-context`
- `POST http://127.0.0.1:8001/packs/import-path`
- `DELETE http://127.0.0.1:8001/packs/{installed_pack_id}`
- `POST http://127.0.0.1:8001/ingest/file-path`

The pack-ingestion response is intentionally compact for LM Studio chat:

- `installed_pack_id`
- `pack`
- `pack_id`
- `title`
- `chunk_count`
- `zip_path`
- `message`

Summary-context responses contain every stored chunk for the requested file or
pack, ordered by `source_id` and `chunk_index`. LM Studio reads that context and
writes the final summary.

## LM Studio Configuration Shape

Use an absolute script path because LM Studio may launch the server outside the
repo working directory.

```json
{
  "mcpServers": {
    "lecture_sense_rag": {
      "command": "/absolute/path/to/sp2/environment/.venv/bin/python",
      "args": [
        "/absolute/path/to/sp2/integrations/lm_studio_mcp/server.py"
      ],
      "env": {
        "SP2_BACKEND_API_BASE_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

The installer creates this JSON with the correct absolute Windows, macOS, or
Linux paths. Windows JSON uses its `.venv\\Scripts\\python.exe` path; JSON
escaping handles the backslashes automatically.

## Implementation Notes

- Keep the MCP layer thin.
- Keep teacher and student business logic in their backend modules.
- Keep retrieval behavior in the student backend.
- Return structured context packets, not final prose answers.
- Avoid broad filesystem access from MCP tools.

Current file split:

- `server.py`: creates `FastMCP`, registers tool groups, and runs stdio.
- `student_tools.py`: student pack, import, retrieval, and summary-context tools.
- `teacher_tools.py`: teacher ingest MCP tools.
- `client.py`: shared HTTP helper for the unified SP2 backend API.
- `validators.py`: MCP argument validation and small payload helpers.
