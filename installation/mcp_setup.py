"""Build and open LM Studio MCP installation links."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from config.arguments import (
    DEFAULT_MCP_SERVER_NAME,
    DEFAULT_SP2_BACKEND_BASE_URL,
    REPO_ROOT,
)


MCP_SERVER_PATH = REPO_ROOT / "integrations" / "lm_studio_mcp" / "server.py"


def _mcp_server_config(python_path: Path) -> dict[str, Any]:
    return {
        "command": str(python_path),
        "args": [str(MCP_SERVER_PATH)],
        "env": {
            "SP2_BACKEND_API_BASE_URL": DEFAULT_SP2_BACKEND_BASE_URL,
        },
    }


def _mcp_config(python_path: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            DEFAULT_MCP_SERVER_NAME: _mcp_server_config(python_path),
        }
    }


def _mcp_install_url(python_path: Path) -> str:
    encoded_config = base64.b64encode(
        json.dumps(
            _mcp_server_config(python_path),
            separators=(",", ":"),
        ).encode("utf-8")
    ).decode("ascii")
    query = urlencode(
        {
            "name": DEFAULT_MCP_SERVER_NAME,
            "config": encoded_config,
        }
    )
    return f"lmstudio://add_mcp?{query}"


def _run_uri_opener(command: list[str], *, env: dict[str, str] | None = None) -> bool:
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _looks_like_lm_studio(name: str) -> bool:
    normalized = "".join(character for character in name.casefold() if character.isalnum())
    return "lmstudio" in normalized


def _registered_linux_handler() -> bool:
    try:
        completed = subprocess.run(
            ["xdg-mime", "query", "default", "x-scheme-handler/lmstudio"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0 and _looks_like_lm_studio(completed.stdout)


def _running_linux_appimage() -> Path | None:
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return None

    for process_dir in proc_dir.iterdir():
        if not process_dir.name.isdigit():
            continue
        try:
            arguments = (process_dir / "cmdline").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        for raw_argument in arguments:
            if not raw_argument:
                continue
            candidate = Path(os.fsdecode(raw_argument))
            if (
                candidate.suffix.casefold() == ".appimage"
                and _looks_like_lm_studio(candidate.name)
                and candidate.is_file()
            ):
                return candidate
    return None


def _installed_linux_app() -> Path | None:
    for command_name in ("lm-studio", "lmstudio"):
        command = shutil.which(command_name)
        if command:
            return Path(command)

    running_appimage = _running_linux_appimage()
    if running_appimage is not None:
        return running_appimage

    home = Path.home()
    for directory in (
        home / "Applications",
        home / "Apps",
        home / ".local" / "bin",
        home / "Downloads",
    ):
        if not directory.is_dir():
            continue
        for candidate in directory.iterdir():
            if (
                candidate.suffix.casefold() == ".appimage"
                and _looks_like_lm_studio(candidate.name)
                and candidate.is_file()
            ):
                return candidate
    return None


def _launch_lm_studio_app() -> bool:
    """Launch the LM Studio app without waiting for it to exit.

    Unlike _open_mcp_install_url, this is for a cold start where no LM Studio
    instance is running yet: the launched process IS the long-running app,
    not a short-lived URL-handoff helper, so it must never be waited on.
    subprocess.run(..., timeout=...) would be wrong here - Python kills the
    child when the timeout elapses, which would kill LM Studio mid-launch.
    """
    try:
        if os.name == "nt":
            os.startfile("lmstudio://")  # type: ignore[attr-defined]
            return True

        if sys.platform == "darwin":
            subprocess.Popen(
                ["open", "lmstudio://"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        if sys.platform.startswith("linux"):
            if _registered_linux_handler():
                subprocess.Popen(
                    ["xdg-open", "lmstudio://"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True

            lm_studio_app = _installed_linux_app()
            if lm_studio_app is None:
                return False
            clean_env = os.environ.copy()
            clean_env.pop("ELECTRON_RUN_AS_NODE", None)
            subprocess.Popen(
                [str(lm_studio_app)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=clean_env,
                start_new_session=True,
            )
            return True
    except OSError:
        return False

    return False


def _open_mcp_install_url(install_url: str) -> bool:
    try:
        if os.name == "nt":
            os.startfile(install_url)  # type: ignore[attr-defined]
            return True

        if sys.platform == "darwin":
            return _run_uri_opener(["open", install_url])

        if sys.platform.startswith("linux"):
            if _registered_linux_handler():
                return _run_uri_opener(["xdg-open", install_url])

            lm_studio_app = _installed_linux_app()
            if lm_studio_app is None:
                return False
            clean_env = os.environ.copy()
            clean_env.pop("ELECTRON_RUN_AS_NODE", None)
            return _run_uri_opener(
                [str(lm_studio_app), install_url],
                env=clean_env,
            )
    except OSError:
        return False

    return False
