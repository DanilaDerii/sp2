# SP2

Local-first course AI assistant platform.

## Python Version

This project targets `Python 3.12.2`.

Use a 3.12 interpreter when creating the virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Locked Starter Stack

- Backend: Python + FastAPI
- Frontend: TypeScript
- Metadata DB: SQLite
- Vector store: LanceDB
- Audio transcription: faster-whisper
- Document parsing/OCR: Docling
- Local model runtime: Ollama

## Local Runtime Prerequisite

`Ollama` is a machine-level dependency and is not installed through `requirements.txt`.

The Python backend will talk to a locally running Ollama instance over HTTP.

## Python Environments

- `requirements.txt`: core backend/runtime dependencies
- `requirements-docs.txt`: heavier document parsing/OCR stack

## Notes

- `requirements.txt` installs Python packages, but it does not lock the Python interpreter version.
- `requirements.txt` does not install Ollama. Ollama must be installed separately on the machine.
- `.python-version` declares the intended interpreter for local setup tools and developers.
- We should later add a startup/version check in the backend so unsupported Python versions fail fast.
