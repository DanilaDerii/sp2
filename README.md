# SP2

SP2 turns local course files into searchable course packs for LM Studio. It
builds and stores the packs, finds relevant course material, and gives that
material to LM Studio. LM Studio writes the final answer.

Supported source files are `.pdf`, `.odt`, `.docx`, and `.pptx`. SP2 can also
install a previously exported SP2 ZIP pack. Legacy `.ppt` files must first be
saved as `.pptx`.

## Requirements

- Python 3.10 or newer
- LM Studio, opened at least once so its `lms` command is available
- LM Studio local-server authentication turned off
- About 6 GB of free disk space
- 16 GB RAM recommended; 8 GB is workable with other large applications closed

The installer prepares two local models:

- Qwen2.5 7B Instruct 1M Q4_K_M for chat, about 4.7 GB
- Nomic Embed Text v1.5 Q4_K_M for 768-number embeddings, about 84 MB

LM Studio may offer its own starter model on first launch. SP2 does not need
that model, so you can skip it.

## Install

### 1. Install and open LM Studio

Download LM Studio from [lmstudio.ai/download](https://lmstudio.ai/download),
install it, and open it once. Restart your terminal afterward if the `lms`
command is not found.

### 2. Run the SP2 installer

Linux or macOS:

```bash
git clone https://github.com/DanilaDerii/sp2.git
cd sp2
python3 installation/script.py
```

Windows PowerShell:

```powershell
git clone https://github.com/DanilaDerii/sp2.git
Set-Location .\sp2
py .\installation\script.py
```

The installer:

- creates `environment/.venv` and installs Python packages;
- creates the local SQLite and LanceDB storage;
- downloads, loads, and checks the required LM Studio models;
- starts the LM Studio local server;
- opens the MCP approval prompt; and
- prints the command for starting the SP2 backend.

Use `--skip-model-setup` only when you want to prepare Python and storage
without downloading or loading the models:

```bash
python3 installation/script.py --skip-model-setup
```

The installer does not start the SP2 backend.

### 3. Approve and enable the MCP tool

At the end of setup, approve the `lecture_sense_rag` server in LM Studio. It
appears in chat as `mcp/lecture-sense-rag`.

Approving the server and enabling it in a chat are separate steps. Open the
chat's Integrations menu and enable `mcp/lecture-sense-rag`. New chats may need
the tool enabled again.

### 4. Start the backend

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

Leave that terminal open. Press `Ctrl+C` there to stop the backend.

After restarting your computer, open LM Studio, make sure the Qwen and Nomic
models and its local server are running, then start the SP2 backend again.

## Use SP2 in LM Studio

You can ask naturally. For example:

```text
Build and install the course file at /home/me/lectures/week02.pdf
List my installed packs
Use pack Week02 - Unit Testing and explain dynamic unit testing
Summarize lecture.pdf from pack Week02 - Unit Testing
Give me an overview of pack Week02 - Unit Testing
Delete installed pack 7
```

Use an absolute path when installing a file, directory, or ZIP pack. A
directory is searched recursively, and all supported files below it are built
into one pack. A newly built pack is also exported to `artifacts/` as a
portable ZIP.

### Pack identifiers

The pack list shows two identifiers:

- `pack_id` is the logical course name stored inside the pack.
- `installed_pack_id` is the numeric row for that exact local installation.

Question and summary tools accept an installed number, `pack_id`, displayed
title, or the original filename of a single-file pack. Text matching ignores
capitalization and whitespace. If more than one pack matches, SP2 asks for a
more exact reference.

Deletion only accepts `installed_pack_id`. This prevents SP2 from guessing
which installation to remove.

### MCP tools

| Tool | Purpose | Arguments |
|---|---|---|
| `sp2_ingest_source` | Build or install a file, directory, or SP2 ZIP pack | `source_path` |
| `sp2_list_packs` | List installed packs | `pack_id`, `active_only` (optional) |
| `sp2_get_course_context` | Find relevant chunks for a question | `pack`, `question` |
| `sp2_get_file_summary_context` | Return all chunks from one source file | `pack`, `source_id` |
| `sp2_get_pack_summary_context` | Return opening chunks from each file | `pack` |
| `sp2_delete_pack` | Delete one exact local installation | `installed_pack_id` |

LM Studio is instructed to answer from returned course chunks and cite their
page numbers. If the returned chunks do not answer the question, it should say
so instead of inventing an answer.

## Test the backend from the CLI

With the backend running, open another terminal in the repository:

```bash
environment/.venv/bin/python -m cli health
environment/.venv/bin/python -m cli packs
environment/.venv/bin/python -m cli context 1 "Explain unit testing"
```

Run `environment/.venv/bin/python -m cli --help` to see every command. The
complete command reference is in [cli/README.md](cli/README.md).

## Local storage

The installer creates local runtime data under:

- `storage/database/sqlite_storage/`
- `storage/database/lance_storage/`
- `storage/installed_packs/`
- `artifacts/`

These directories are ignored by Git. Each teammate creates their own empty
databases during installation and installs their own packs.

To preview a storage reset:

```bash
environment/.venv/bin/python -m cli.cli_clearOut
```

To remove installed packs and recreate SQLite and LanceDB:

```bash
environment/.venv/bin/python -m cli.cli_clearOut --yes
```

Stop the backend before clearing storage. Exported ZIP files in `artifacts/`
are kept.

## How it works

```text
LM Studio chat
    -> SP2 MCP server
    -> SP2 FastAPI backend
    -> teacher pack builder or student retrieval
    -> SQLite and LanceDB
    -> structured course context returned to LM Studio
```

LM Studio owns chat, model selection, and final wording. SP2 owns course-pack
creation, installation, storage, and retrieval.

## Troubleshooting

### The CLI or MCP cannot connect

Make sure the backend terminal is still running, then check:

```bash
environment/.venv/bin/python -m cli health
```

A successful response is:

```json
{
  "status": "ok"
}
```

If port 8001 is already in use, an older backend is probably still running.
Try the health command before starting another copy.

### The MCP approval prompt did not open

The installer prints an installation link and fallback JSON when it cannot
open LM Studio automatically. You can also edit LM Studio's MCP configuration:

- Linux and macOS: `~/.lmstudio/mcp.json`
- Windows: `%USERPROFILE%\.lmstudio\mcp.json`

The entry should use absolute paths to your repository:

```json
{
  "mcpServers": {
    "lecture_sense_rag": {
      "command": "/path/to/sp2/environment/.venv/bin/python",
      "args": ["/path/to/sp2/integrations/lm_studio_mcp/server.py"],
      "env": {
        "SP2_BACKEND_API_BASE_URL": "http://127.0.0.1:8001"
      }
    }
  }
}
```

Saving `mcp.json` reloads the MCP server. Enable the tool in the chat after it
appears.

### Setup was interrupted

Run the installer again. It reuses the existing virtual environment and local
storage. LM Studio also reuses model files that finished downloading.

For MCP implementation details, see
[integrations/lm_studio_mcp/README.md](integrations/lm_studio_mcp/README.md).
