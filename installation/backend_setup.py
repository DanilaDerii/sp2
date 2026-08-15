"""Start the SP2 backend and print its reusable start command."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from config.arguments import DEFAULT_SP2_BACKEND_BASE_URL, REPO_ROOT
from installation.setup_helpers import SetupError, _command_text, _ok, _print_step


BACKEND_WAIT_SECONDS = 30


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


def _backend_is_ready() -> bool:
    health_url = f"{DEFAULT_SP2_BACKEND_BASE_URL.rstrip('/')}/health"
    request = Request(health_url, method="GET")
    try:
        with urlopen(request, timeout=2) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, OSError):
        return False


def _start_backend(python_path: Path) -> bool:
    _print_step("Starting the SP2 backend")
    if _backend_is_ready():
        _ok(f"SP2 backend is already running at {DEFAULT_SP2_BACKEND_BASE_URL}")
        return False

    process_options: dict[str, object] = {
        "cwd": REPO_ROOT,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        process_options["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        process_options["start_new_session"] = True

    command = _backend_command(python_path)
    try:
        process = subprocess.Popen(
            command,
            **process_options,
        )
    except OSError as exc:
        raise SetupError(f"Could not start the SP2 backend: {exc}") from exc

    deadline = time.monotonic() + BACKEND_WAIT_SECONDS
    while time.monotonic() < deadline:
        if _backend_is_ready():
            _ok(
                f"SP2 backend is running at {DEFAULT_SP2_BACKEND_BASE_URL} "
                f"(process {process.pid})"
            )
            return True
        exit_code = process.poll()
        if exit_code is not None:
            raise SetupError(
                "SP2 backend stopped during startup with exit code "
                f"{exit_code}. Run this command from {REPO_ROOT} to see its error: "
                f"{_command_text(command)}"
            )
        time.sleep(1)

    process.terminate()
    raise SetupError(
        f"SP2 backend did not become ready within {BACKEND_WAIT_SECONDS} seconds"
    )


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


def _print_future_backend_command(python_path: Path) -> None:
    _print_step("Backend command for future starts")
    print("The backend is running now.")
    print("After a restart, use these commands to start it again:")
    print()
    _print_backend_command(python_path)
    print()
    print("When started this way, press Ctrl+C to stop it.")
