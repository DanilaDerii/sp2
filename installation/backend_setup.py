"""Build and print the command used to start the SP2 backend."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from config.arguments import DEFAULT_SP2_BACKEND_BASE_URL, REPO_ROOT
from installation.setup_helpers import _print_step


def _backend_address() -> tuple[str, int]:
    backend_url = urlsplit(DEFAULT_SP2_BACKEND_BASE_URL)
    return backend_url.hostname or "127.0.0.1", backend_url.port or 8001


def _backend_command(python_path: Path) -> list[str]:
    backend_host, backend_port = _backend_address()
    return [
        str(python_path),
        "-m",
        "uvicorn",
        "backend.api.api:app",
        "--host",
        backend_host,
        "--port",
        str(backend_port),
    ]


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _print_backend_command(python_path: Path) -> None:
    command = _backend_command(python_path)

    if os.name == "nt":
        print("PowerShell:")
        print(f"Set-Location -LiteralPath {_powershell_quote(str(REPO_ROOT))}")
        print("& " + " ".join(_powershell_quote(argument) for argument in command))
        print()
        print("Command Prompt:")
        print(f'cd /d "{REPO_ROOT}"')
        print(subprocess.list2cmdline(command))
        return

    print(f"cd {shlex.quote(str(REPO_ROOT))}")
    print(shlex.join(command))


def _print_backend_start_command(python_path: Path) -> None:
    _print_step("Start the backend")
    print("Setup does not start the backend automatically.")
    print("Run these commands in a terminal when you are ready:")
    print()
    _print_backend_command(python_path)
    print()
    print("When started this way, press Ctrl+C to stop it.")
