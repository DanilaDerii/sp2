"""Setup the local SP2 Python environment and storage."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / "environment" / ".venv"
REQUIREMENTS_PATH = REPO_ROOT / "environment" / "requirements.txt"
MCP_SERVER_PATH = REPO_ROOT / "integrations" / "lm_studio_mcp" / "server.py"
SP2_BACKEND_API_BASE_URL = "http://127.0.0.1:8001"


class SetupError(RuntimeError):
    """Raised when a required setup step fails."""


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _print_step(message: str) -> None:
    print(f"\n==> {message}")


def _ok(message: str) -> None:
    print(f"[ok] {message}")


def _run(command: list[str], *, cwd: Path = REPO_ROOT) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise SetupError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def _create_venv() -> Path:
    _print_step("Creating Python virtual environment")
    python_path = _venv_python()
    if python_path.exists():
        _ok(f"Virtual environment already exists: {VENV_DIR}")
        return python_path

    _run([sys.executable, "-m", "venv", str(VENV_DIR)])
    if not python_path.exists():
        raise SetupError(f"Virtual environment Python was not created: {python_path}")
    _ok(f"Created virtual environment: {VENV_DIR}")
    return python_path


def _install_requirements(python_path: Path) -> None:
    _print_step("Installing Python dependencies")
    if not REQUIREMENTS_PATH.is_file():
        raise SetupError(f"Requirements file not found: {REQUIREMENTS_PATH}")
    _run([str(python_path), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    _ok(f"Installed dependencies from: {REQUIREMENTS_PATH}")


def _initialize_storage(python_path: Path) -> None:
    _print_step("Initializing SP2 storage")
    _run([str(python_path), "-m", "storage.database.setup.create_sqlite_db"])
    _ok("SQLite database is ready")
    _run([str(python_path), "-m", "storage.database.setup.create_lancedb_db"])
    _ok("LanceDB table is ready")


def _mcp_config(python_path: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            "sp2-course-context": {
                "command": str(python_path),
                "args": [str(MCP_SERVER_PATH)],
                "env": {
                    "SP2_BACKEND_API_BASE_URL": SP2_BACKEND_API_BASE_URL,
                },
            }
        }
    }


def _print_next_steps(python_path: Path) -> None:
    backend_command = (
        f"cd {REPO_ROOT}\n"
        f"{python_path} -m uvicorn backend.api.api:app --host 127.0.0.1 --port 8001"
    )

    _print_step("Next: start LM Studio server")
    print("Start LM Studio's local server from the LM Studio UI or with:")
    print()
    print("lms server start")

    _print_step("Next: add SP2 MCP config in LM Studio")
    print("Paste this JSON into LM Studio's MCP/server configuration:")
    print(json.dumps(_mcp_config(python_path), indent=2))

    _print_step("Next: start SP2 backend")
    print("Run this command when you want to use SP2 tools:")
    print()
    print(backend_command)
    print()
    print("To stop the backend afterward, press Ctrl+C in that terminal.")


def main() -> int:
    print("SP2 setup")
    print(f"Repo root: {REPO_ROOT}")

    try:
        python_path = _create_venv()
        _install_requirements(python_path)
        _initialize_storage(python_path)
        _print_next_steps(python_path)
    except SetupError as exc:
        print()
        print(f"[error] {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("[error] Setup interrupted")
        return 130

    print()
    _ok("SP2 setup finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
