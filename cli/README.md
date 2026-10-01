# Backend API CLI

This CLI lets you call and test the running SP2 backend from another terminal.

Start the backend from the project root:

```bash
environment/.venv/bin/python -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001
```

Leave that terminal open. In a second terminal, run any of these commands:

```bash
# Check the backend
environment/.venv/bin/python -m cli health

# List installed packs
environment/.venv/bin/python -m cli packs

# Get one pack by its installed_pack_id
environment/.venv/bin/python -m cli pack 1

# Build or install a file, directory, or SP2 ZIP pack
environment/.venv/bin/python -m cli install "/absolute/path/to/course.pdf"

# Ask a question using one installed pack
environment/.venv/bin/python -m cli context 1 "Explain unit testing"

# Get summary context for one file
environment/.venv/bin/python -m cli file-summary 1 "lecture.pdf"

# Get summary context for a complete pack
environment/.venv/bin/python -m cli pack-summary 1

# Delete one pack
environment/.venv/bin/python -m cli delete-pack 1 --yes
```

The number in these commands is the exact `installed_pack_id` returned by the
`packs` command. Deletion is not sent unless `--yes` is included.

To see all commands and options:

```bash
environment/.venv/bin/python -m cli --help
environment/.venv/bin/python -m cli context --help
```

The CLI uses `http://127.0.0.1:8001` by default. To use another backend URL,
set `SP2_BACKEND_API_BASE_URL` before running the command.

## Clear Local Storage

`cli_clearOut.py` is separate from the backend API commands. It clears the
installed student packs and recreates the local SQLite and LanceDB storage.
ZIP files saved in `artifacts/` are kept.

Stop the backend before clearing its storage.

Preview the operation without deleting anything:

```bash
environment/.venv/bin/python -m cli.cli_clearOut
```

Perform the reset:

```bash
environment/.venv/bin/python -m cli.cli_clearOut --yes
```

The reset only happens when `--yes` is included.
