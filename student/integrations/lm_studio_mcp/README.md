# SP2 LM Studio MCP Integration

This directory is reserved for the LM Studio MCP server that will expose SP2 student retrieval as local tools.

The intended runtime boundary is:

```text
LM Studio chat UI
-> LM Studio MCP host/client
-> SP2 MCP server
-> SP2 student FastAPI API
-> SQLite/LanceDB retrieval
-> context packet back to LM Studio
```

The MCP server should not generate final answers. LM Studio owns chat, model selection, and final answer generation. SP2 owns pack import, question embedding, retrieval, and returning structured context.

Planned tools:

- `sp2_list_packs()`
- `sp2_get_pack(installed_pack_id)`
- `sp2_get_course_context(installed_pack_id, question, top_k=None, max_distance=None)`
- `sp2_import_pack_from_path(pack_zip_path)`

Planned local API dependency:

- `GET http://127.0.0.1:8001/packs`
- `GET http://127.0.0.1:8001/packs/{installed_pack_id}`
- `POST http://127.0.0.1:8001/retrieval/context`
- `POST http://127.0.0.1:8001/packs/import-path`

Expected LM Studio configuration shape:

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

Before connecting from LM Studio, the student FastAPI server should be running:

```bash
student/environment/.venv/bin/python -m uvicorn student.backend.app:app --host 127.0.0.1 --port 8001
```

Implementation notes:

- Keep the MCP layer thin.
- Keep retrieval behavior in the existing student backend.
- Return structured context packets, not final prose answers.
- Avoid broad filesystem access from MCP tools.
