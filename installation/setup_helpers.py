"""Python, storage, and command-output helpers for SP2 setup."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from config.arguments import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_LLM_MODEL,
    DEFAULT_MCP_SERVER_NAME,
    REPO_ROOT,
)
from installation.mcp_setup import (
    _mcp_config,
    _mcp_install_url,
    _open_mcp_install_url,
)


VENV_DIR = REPO_ROOT / "environment" / ".venv"
REQUIREMENTS_PATH = REPO_ROOT / "environment" / "requirements.txt"


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


def _command_text(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _run(
    command: list[str],
    *,
    cwd: Path = REPO_ROOT,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=capture_output,
            text=True,
        )
    except OSError as exc:
        raise SetupError(
            f"Could not run command: {_command_text(command)} ({exc})"
        ) from exc

    if completed.returncode != 0:
        detail = ""
        if capture_output:
            detail = (completed.stderr or completed.stdout or "").strip()
        detail_suffix = f"\n{detail}" if detail else ""
        raise SetupError(
            f"Command failed with exit code {completed.returncode}: "
            f"{_command_text(command)}{detail_suffix}"
        )
    return completed


def _check_python_version() -> None:
    _print_step("Checking system prerequisites")
    if sys.version_info < (3, 10):
        raise SetupError(
            "SP2 requires Python 3.10 or newer; "
            f"current interpreter is Python {sys.version_info.major}."
            f"{sys.version_info.minor}"
        )
    _ok(f"Python {sys.version_info.major}.{sys.version_info.minor} is supported")


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
    _ok(f"LanceDB is ready for {DEFAULT_EMBEDDING_DIM}-dimensional vectors")


def _print_next_steps(python_path: Path, *, model_setup_complete: bool) -> None:
    if model_setup_complete:
        _print_step("LM Studio models are ready")
        print(f"Embedding model loaded as: {DEFAULT_EMBEDDING_MODEL}")
        print(f"Chat model loaded as: {DEFAULT_LLM_MODEL}")
    else:
        _print_step("LM Studio model setup was skipped")
        print("Download and load the required models before ingesting course files.")

    _print_step("Connect SP2 to LM Studio")
    install_url = _mcp_install_url(python_path)
    if _open_mcp_install_url(install_url):
        _ok("Opened LM Studio's MCP approval prompt")
        print(f"Approve '{DEFAULT_MCP_SERVER_NAME}' in LM Studio.")
    else:
        print("Could not open LM Studio automatically.")
        print("Open this link to show the MCP approval prompt:")
        print(install_url)
        print()
        print("If the link does not open, paste this JSON into LM Studio's mcp.json:")
        print(json.dumps(_mcp_config(python_path), indent=2))
