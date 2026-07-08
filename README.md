# SP2 Installation

SP2 is a local course-pack and retrieval tool for LM Studio. LM Studio owns the
chat UI and final answer. SP2 owns course-pack storage, retrieval, and the MCP
tool that returns course context.

## 1. Install And Open LM Studio

Install LM Studio and open it at least once before using the `lms` command.

## 2. Download And Load The Embedding Model

In LM Studio, download and load:

```text
text-embedding-nomic-embed-text-v1.5
```

SP2 expects this model to return 768-dimensional embedding vectors.

## 3. Run The SP2 Setup Script

From a terminal, go to the folder where you cloned or copied SP2, then run:

```bash
cd /path/to/sp2
python3 installation/script.py
```

The setup script creates or reuses `environment/.venv`, installs
`environment/requirements.txt`, initializes SQLite and LanceDB, then prints the
MCP JSON and backend start command.

The setup script does not start LM Studio, edit `mcp.json`, download models, or
start the SP2 backend.

## 4. Start The LM Studio Server

Start LM Studio's local server from the LM Studio UI, or run:

```bash
lms server start
```

SP2 will use LM Studio's local embeddings endpoint automatically after the
server is running.

## 5. Add The MCP Config In LM Studio

In LM Studio, open:

```text
Developer tab -> Local Server -> mcp.json
of if you havent enabled developer mode on installation first go:
Open LM Studio → Settings → Developer → turn on Developer Mode.
```

If `mcp.json` is empty, paste this full JSON:

```json
{
  "mcpServers": {
    "sp2-course-context": {
      "command": "/path/to/sp2/environment/.venv/bin/python",
      "args": [
        "/path/to/sp2/integrations/lm_studio_mcp/server.py"
      ],
      "env": {
        "SP2_BACKEND_API_BASE_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

If it already has `"mcpServers": { ... }`, paste only the
`"sp2-course-context": { ... }` entry inside that object.

Replace `/path/to/sp2` with your real SP2 folder path. The setup script prints
the same config with the correct absolute paths for your machine.

## 6. Start The SP2 Backend

Use the backend command printed by the setup script. It will use the real path on
your machine and will look like this:

```bash
cd /path/to/sp2
/path/to/sp2/environment/.venv/bin/python -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

Leave that terminal running while using SP2 from LM Studio.

To stop the backend later, press:

```text
Ctrl+C
```

## 7. Ingest Or Import A Teacher Source File

Keep the LM Studio server and SP2 backend running first.

Supported teacher source files:

```text
.pdf
.odt
.docx
```

To let LM Studio build and import a pack through MCP, use:

```text
Use mcp/sp2-course-context. Import this file: /path/to/teacher-file.odt
```

The tool returns the installed pack id. Use that id for retrieval questions.


## 8. Prompt LM Studio To Use SP2

For consistent demos, ask LM Studio directly to use the SP2 course-context tool
before answering.

Use this prompt shape:

```
Use mcp/sp2-course-context tool.
pack: <installed_pack_id>
question: <your question here>

After the tool returns, answer in normal prose using the returned course chunks.
If the returned chunks do not contain the answer, say the course pack does not
contain it.
```

If you need pack deleted: 

'''
Use mcp/sp2-course-context.
delete pack 1
'''

## Important

Two local servers are involved:

```text
LM Studio server: http://127.0.0.1:1234/v1
SP2 backend:      http://127.0.0.1:8001
```

LM Studio and the SP2 backend must both be running for SP2 tools to work.

## Storage Maintenance

To reset local SP2 storage during development:

```bash
cd /path/to/sp2
environment/.venv/bin/python -m storage.database.setup.reset_student_databases --yes
find storage/installed_packs -mindepth 1 -maxdepth 1 ! -name .gitkeep -exec rm -rf {} +
find artifacts -mindepth 1 -maxdepth 1 ! -name .gitkeep -exec rm -rf {} +
```
