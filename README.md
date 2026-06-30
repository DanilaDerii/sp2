# SP2 Installation

SP2 is a local course-pack and retrieval tool for LM Studio. LM Studio owns the
chat UI and final answer. SP2 owns course-pack storage, retrieval, and the MCP
tool that returns course context.

## 1. Install LM Studio

Install and open LM Studio first.

## 2. Download The Embedding Model

In LM Studio, search for and download:

```text
text-embedding-nomic-embed-text-v1.5
```

SP2 expects this model to return 768-dimensional embedding vectors.

## 3. Start The LM Studio Server

In LM Studio, open the local server/developer area and start the server.

Use the default OpenAI-compatible base URL:

```text
http://127.0.0.1:1234/v1
```

## 4. Run The SP2 Installer

From a terminal, go to the folder where you cloned or copied SP2, then run:

```bash
cd /path/to/sp2
python3 installation/script.py
```

The installer creates the Python virtual environment, installs requirements,
initializes SQLite/LanceDB storage, checks LM Studio embeddings when available,
briefly tests the SP2 backend, stops that temporary backend, then prints the MCP
JSON and backend start command.

## 5. Add The MCP Config In LM Studio

Copy the MCP JSON printed by the installer.

In LM Studio, open:

```text
Program tab -> Install -> Edit mcp.json
```

If `mcp.json` is empty, paste the full JSON.

If it already has `"mcpServers": { ... }`, paste only the
`"sp2-course-context": { ... }` entry inside that object.

## 6. Start The SP2 Backend

Use the backend command printed by the installer. It will use the real path on
your machine and will look like:

```bash
cd /path/to/sp2
/path/to/sp2/environment/.venv/bin/python -m uvicorn student.backend.app:app --host 127.0.0.1 --port 8001
```

Leave that terminal running while using SP2 from LM Studio.

To stop the backend later, press:

```text
Ctrl+C
```

## Important

Two local servers are involved:

```text
LM Studio server: http://127.0.0.1:1234/v1
SP2 backend:      http://127.0.0.1:8001
```

Both must be running when LM Studio uses SP2 retrieval.
