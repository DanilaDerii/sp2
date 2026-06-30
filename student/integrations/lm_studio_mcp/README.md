# SP2 LM Studio MCP Integration

Last audited: 2026-06-30

This directory contains the implemented MCP server that exposes SP2 student
retrieval as local tools for LM Studio.

The runtime boundary is:

```text
LM Studio chat UI
-> LM Studio MCP host/client
-> SP2 MCP stdio server
-> SP2 student FastAPI API
-> SQLite/LanceDB retrieval
-> context packet back to LM Studio
```

LM Studio owns chat, model selection, and final answer generation. SP2 owns pack
import, query embedding calls/configuration, retrieval, and structured context
packets.

Direction note: the current code still embeds through Ollama, but the target
direction is to use LM Studio's local OpenAI-compatible embeddings API as the
embedding provider for both teacher pack creation and student query retrieval.
MCP remains the tool boundary for course-context calls.

## Tools

- `sp2_list_packs(pack_id=None, active_only=False)`
- `sp2_get_pack(installed_pack_id)`
- `sp2_get_course_context(installed_pack_id, question, top_k=None, max_distance=None)`
- `sp2_import_pack_from_path(pack_zip_path)`

## Local API Dependency

The student FastAPI server should be running before LM Studio calls the MCP
server:

```bash
student/environment/.venv/bin/python -m uvicorn student.backend.app:app --host 127.0.0.1 --port 8001
```

The MCP tools call:

- `GET http://127.0.0.1:8001/packs`
- `GET http://127.0.0.1:8001/packs/{installed_pack_id}`
- `POST http://127.0.0.1:8001/retrieval/context`
- `POST http://127.0.0.1:8001/packs/import-path`

## LM Studio Configuration Shape

Use an absolute script path because LM Studio may launch the server outside the
repo working directory.

```json
{
  "mcpServers": {
    "sp2-course-context": {
      "command": "/home/d/sp2/student/environment/.venv/bin/python",
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

## Implementation Notes

- Keep the MCP layer thin.
- Keep retrieval behavior in the student backend.
- Return structured context packets, not final prose answers.
- Avoid broad filesystem access from MCP tools.
