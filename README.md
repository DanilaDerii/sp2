# SP2

SP2 turns local course files into searchable packs for LM Studio. SP2 stores and
searches the course material; LM Studio provides the chat and final answer.

## Prerequisites

- Python 3.10 or newer
- pip
- LM Studio installed and opened at least once
- LM Studio local server authentication turned off
- Internet access and about 6 GB of free space
- 8 GB RAM recommended (4 GB minimum); SP2 keeps LM Studio and a chat model
  loaded at the same time, so expect slower performance or occasional
  instability below 8 GB
- A local copy of this repository

No models or document tools need to be installed manually. The setup script
handles them.

## Install

Linux or macOS:

```bash
git clone https://github.com/DanilaDerii/sp2.git
cd sp2
```

```bash
cd /path/to/sp2
python3 installation/script.py
```

Windows PowerShell:

```powershell
git clone https://github.com/DanilaDerii/sp2.git
Set-Location .\sp2
```

```powershell
Set-Location -LiteralPath 'C:\path\to\sp2'
py .\installation\script.py
```

The script:

- creates the Python environment and installs dependencies;
- creates SQLite and LanceDB;
- downloads and loads the Nomic embedding model;
- downloads and loads the Qwen chat model;
- starts the LM Studio server and SP2 backend;
- opens LM Studio's MCP approval prompt;
- prints the backend command for future starts.

## Approve the LM Studio Tool

When LM Studio asks to add `lecture_sense_rag`, approve it. LM Studio displays
the tool in chat as:

```text
mcp/lecture-sense-rag
```

Open a new chat and make sure this tool is enabled. If the approval prompt does
not open, use the installation link or `mcp.json` content printed by the setup
script.

## Start the Backend Later

The installer starts the backend automatically. After restarting your device,
open LM Studio, start its local server, load the Qwen and Nomic models, and then
start the SP2 backend.

Linux or macOS:

```bash
cd /path/to/sp2
environment/.venv/bin/python -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

Windows PowerShell:

```powershell
Set-Location -LiteralPath 'C:\path\to\sp2'
& '.\environment\.venv\Scripts\python.exe' -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

Leave that terminal open. Press `Ctrl+C` to stop the backend.

## Supported Course Files

SP2 supports `.pdf`, `.odt`, `.docx`, and `.pptx`. Legacy `.ppt` files must be
saved as `.pptx` first.

You can provide one exact file or a directory. A directory is searched
recursively and its supported files are combined into one pack.

Use absolute paths. Windows paths are supported.

## MCP Prompt Examples

Replace the example paths and pack numbers with your own values.

### Build and install a pack

Tool: `sp2_ingest_file_from_path`

```text
Use mcp/lecture-sense-rag.
Call sp2_ingest_file_from_path with:
file_path: /absolute/path/to/course-file-or-directory
```

This builds a portable ZIP, installs it, and returns its numeric installed pack
ID.

The ZIP is saved in the repository's `artifacts/` directory:

```text
<sp2-repository>/artifacts/<pack-id>.zip
```

The tool response also returns its exact `zip_path`. Copy that ZIP to another
device and import it there with `sp2_import_pack_from_path`.

### Import an existing pack ZIP

Tool: `sp2_import_pack_from_path`

```text
Use mcp/lecture-sense-rag.
Call sp2_import_pack_from_path with:
pack_zip_path: /absolute/path/to/course-pack.zip
```

### List installed packs

Tool: `sp2_list_packs`

```text
Use mcp/lecture-sense-rag.
Call sp2_list_packs with:
pack_id: null
active_only: false
```

The returned numeric `id` is used by the next tools.

### Show one installed pack

Tool: `sp2_get_pack`

```text
Use mcp/lecture-sense-rag.
Call sp2_get_pack with:
installed_pack_id: 1
```

### Ask a question

Tool: `sp2_get_course_context`

```text
Use mcp/lecture-sense-rag.
Call sp2_get_course_context with:
pack: 1
question: What are the prerequisites for this course?

After the tool returns, answer using the returned course chunks.
If the chunks do not contain the answer, say so.
```

### Delete an installed pack

Tool: `sp2_delete_pack`

```text
Use mcp/lecture-sense-rag.
Call sp2_delete_pack with:
pack: 1
```

This deletes the installed files, database row, and vectors. ZIP files in
`artifacts/` are kept.

## Clear Local Storage

Linux or macOS:

```bash
cd /path/to/sp2
environment/.venv/bin/python -m cli.cli_clearOut --yes
```

Windows PowerShell:

```powershell
Set-Location -LiteralPath 'C:\path\to\sp2'
& '.\environment\.venv\Scripts\python.exe' -m cli.cli_clearOut --yes
```

This removes installed packs and recreates SQLite and LanceDB. ZIP files in
`artifacts/` are kept.
