# SP2

SP2 turns local course files into searchable packs for LM Studio. SP2 stores and
searches the course material; LM Studio provides the chat and final answer.

## Before You Start: Hardware

**SP2 needs a mid-range machine or better.** It keeps LM Studio, a 4B chat
model, and an embedding model in memory at the same time, and that combination
is genuinely demanding.

| | RAM | What to expect |
|---|---|---|
| **Recommended** | 16 GB or more | Runs comfortably |
| **Workable** | 8-16 GB | Fine, but close browsers and IDEs while using SP2 |
| **Not recommended** | under 8 GB | Slow, and the operating system may kill LM Studio mid-use |

That last row is not theoretical. On a 7.5 GB development machine, the Linux
out-of-memory killer terminated LM Studio four separate times during testing,
once taking the whole desktop session down with it. The installer prints an
advisory warning if it detects under 8 GB, but it will not stop you.

**Disk: plan for about 12 GB free, not 6 GB.** SP2's own models are modest
(2.5 GB chat model, 84 MB embedding model), but LM Studio downloads a default
model of its own on first launch, which was 6.3 GB in our testing. Total model
storage on the development machine ended up at 8.3 GB, plus the Python
environment and your course packs.

## Prerequisites

- Python 3.10 or newer
- pip
- LM Studio installed and opened at least once
- LM Studio local server authentication turned off
- Internet access and about 12 GB of free disk space
- 8 GB RAM minimum, 16 GB recommended (see the table above)
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

## MCP Tool Reference

SP2 registers eight tools. All of them appear in LM Studio under
`mcp/lecture-sense-rag`.

| Tool | What it does | Arguments |
|---|---|---|
| `sp2_ingest_file_from_path` | Build a pack from a file or folder, and install it | `file_path` |
| `sp2_import_pack_from_path` | Install a pack ZIP built elsewhere | `pack_zip_path` |
| `sp2_list_packs` | List installed packs | `pack_id`, `active_only` (both optional) |
| `sp2_get_pack` | Show details for one pack | `installed_pack_id` |
| `sp2_get_course_context` | Search a pack and return the most relevant chunks | `pack`, `question` |
| `sp2_get_file_summary_context` | Return **every** chunk from one file, to summarize | `pack`, `source_id` |
| `sp2_get_pack_summary_context` | Return **every** chunk from a pack, to summarize | `pack` |
| `sp2_delete_pack` | Remove an installed pack | `pack` |

**Naming a pack.** Anywhere a tool takes `pack`, you can use either the number
from `sp2_list_packs` or the pack's name, so `1`, `"1"`, and `"music"` all
work. The one exception is `sp2_delete_pack`, which requires the number on
purpose: a deletion should never be ambiguous about which pack it removes.

## Talking to SP2

You do not need to name tools or arguments. Ask in plain language and LM Studio
picks the tool. The examples below show a natural phrasing first, with the
literal tool call underneath for when you want to be exact.

**One phrasing tip that matters more than it should.** Mention your course
material in the question. "What are the goals in music therapy?" often gets
answered from the model's general knowledge without ever searching your pack;
"What does my course material say about music therapy goals?" reliably searches
it. Answers that cite page numbers came from your pack; answers without them
may not have.

### Build a pack from your course files

> Build a course pack from /home/me/lectures/psych101

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_ingest_file_from_path with:
file_path: /absolute/path/to/course-file-or-directory
```
</details>

This builds a portable ZIP, installs it, and returns the pack's number. The ZIP
is saved to `<sp2-repository>/artifacts/<pack-id>.zip`, and the response
includes the exact `zip_path`. Copy that ZIP to another device to share the
pack.

### Install a pack somebody sent you

> Import the course pack at /home/me/Downloads/psych101.zip

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_import_pack_from_path with:
pack_zip_path: /absolute/path/to/course-pack.zip
```
</details>

### See what is installed

> Which course packs do I have?

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_list_packs with:
pack_id: null
active_only: false
```
</details>

For detail on a single pack:

> Show me the details of pack 1

### Ask a question about a course

> What does my course material say about the prerequisites for this course?

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_get_course_context with:
pack: 1
question: What are the prerequisites for this course?

After the tool returns, answer using the returned course chunks.
If the chunks do not contain the answer, say so.
```
</details>

This searches the pack and returns the most relevant passages with their page
numbers, so answers can cite where they came from.

### Summarize a whole file or pack

> Summarize lecture.pdf from my psych101 pack

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_get_file_summary_context with:
pack: 1
source_id: lecture.pdf

Then summarize all returned chunks.
```

For the complete pack, use `sp2_get_pack_summary_context` with just `pack`.
</details>

Unlike asking a question, these return **every** stored chunk in order rather
than searching for relevant ones. `source_id` is the file's name as stored in
the pack, for example `lecture.pdf`. Large packs can fill a big share of the
model's context window.

### Delete a pack

> Delete pack 1

<details><summary>Explicit form</summary>

```text
Use mcp/lecture-sense-rag.
Call sp2_delete_pack with:
pack: 1
```
</details>

This removes the installed files, database row, and vectors. ZIP files in
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

## Where to Find Things in LM Studio

### Finding `mcp.json` in LM Studio

SP2 writes its entry into LM Studio's `mcp.json`. If the approval prompt never
appeared, or the tool stopped working after you moved the repository, this is
the file to check.

**Step 1 - open the Developer tab, then Local Server.** The Developer tab is
the terminal icon in the far-left sidebar. The `mcp.json` button sits along the
top of that panel, next to Server Settings.

![Opening the Developer tab and the mcp.json button](Documentation/screenshots/mcp-json-step1.jpg)

**Step 2 - check the entry.** The editor opens with the current config. Saving
reloads the MCP servers, so you can fix a wrong path here without restarting
LM Studio.

![The Edit mcp.json dialog showing the SP2 entry](Documentation/screenshots/mcp-json-step2.jpg)

Both paths must point at **your** copy of the repository:

```json
{
  "mcpServers": {
    "lecture_sense_rag": {
      "command": "/path/to/sp2/environment/.venv/bin/python",
      "args": ["/path/to/sp2/integrations/lm_studio_mcp/server.py"],
      "env": { "SP2_BACKEND_API_BASE_URL": "http://127.0.0.1:8001" }
    }
  }
}
```

On Windows, `command` ends with `environment\.venv\Scripts\python.exe` instead.

If you would rather edit the file directly, it lives at `~/.lmstudio/mcp.json`
on Linux and macOS, and `%USERPROFILE%\.lmstudio\mcp.json` on Windows.

### Turning the tool on in a chat

Approving `lecture_sense_rag` once is not the same as enabling it in a chat.
Every new chat has its own tool toggles, and a chat with the tool switched off
will answer from the model's own knowledge without ever touching your course
material.

![The Integrations panel with mcp/lecture-sense-rag enabled, and a tool call in the chat](Documentation/screenshots/enable-tool-in-chat.jpg)
