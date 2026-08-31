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
MCP_CONFIG_PATH = Path.home() / ".lmstudio" / "mcp.json"
_SP2_SERVER_PATH_SUFFIX = "integrations/lm_studio_mcp/server.py"

# Electron's singleton-instance lock files for LM Studio on Linux. When the
# app is killed abruptly (crash, OOM kill) rather than exiting normally,
# these are left behind, and every subsequent launch attempt silently exits
# immediately because Electron thinks another instance is already running.
LM_STUDIO_CONFIG_DIR = Path.home() / ".config" / "LM Studio"
LM_STUDIO_LOCK_PATHS = (
    LM_STUDIO_CONFIG_DIR / "SingletonLock",
    LM_STUDIO_CONFIG_DIR / "Session Storage" / "LOCK",
    LM_STUDIO_CONFIG_DIR / "Local Storage" / "leveldb" / "LOCK",
)


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


def _is_sp2_mcp_entry(entry: dict[str, Any]) -> bool:
    """True if this mcp.json entry's args point at SP2's own MCP server.

    Matches on path shape rather than the server's current name, so it
    catches entries left over from any past install regardless of what key
    they were registered under or which repo path they pointed at.
    """
    args = entry.get("args")
    if not isinstance(args, list):
        return False
    return any(
        isinstance(arg, str) and arg.replace("\\", "/").endswith(_SP2_SERVER_PATH_SUFFIX)
        for arg in args
    )


def _is_stale_sp2_entry(key: str, entry: dict[str, Any]) -> bool:
    """True if an SP2-owned entry is under an old key or points at dead paths."""
    if key != DEFAULT_MCP_SERVER_NAME:
        return True

    command = entry.get("command")
    if isinstance(command, str) and not Path(command).is_file():
        return True

    args = entry.get("args")
    if isinstance(args, list):
        for arg in args:
            if isinstance(arg, str) and not Path(arg).is_file():
                return True

    return False


def _prune_stale_mcp_entries() -> list[str]:
    """Remove stale SP2 entries from mcp.json, leaving everything else alone.

    Only ever removes dead entries; never adds or changes a live one - adding
    a new MCP server stays gated behind LM Studio's own approval UI via the
    add_mcp deep link, since that grants a new capability and removal does
    not. Returns the list of removed keys, or [] if there was nothing to do.
    """
    if not MCP_CONFIG_PATH.is_file():
        return []

    try:
        config = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[warning] Could not read {MCP_CONFIG_PATH}, skipping cleanup: {exc}")
        return []

    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        return []

    stale_keys = [
        key
        for key, entry in servers.items()
        if isinstance(entry, dict) and _is_sp2_mcp_entry(entry) and _is_stale_sp2_entry(key, entry)
    ]
    if not stale_keys:
        return []

    for key in stale_keys:
        del servers[key]

    try:
        MCP_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[warning] Could not write {MCP_CONFIG_PATH}, skipping cleanup: {exc}")
        return []

    return stale_keys


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


def _lm_studio_process_running() -> bool:
    """Scan /proc for any process that looks like LM Studio, of any kind.

    Broader than _running_linux_appimage, which only matches .AppImage
    installs - this also catches .deb/.rpm/Flatpak installs by checking each
    process's short name (comm) and its own executable (argv[0]). Used as a
    safety check before ever deleting a lock file: a false negative here
    (reporting "not running" when it actually is) is the dangerous failure
    mode, so this errs toward matching broadly - but only against the
    process's own identity (comm, argv[0]), never against arbitrary
    arguments. An earlier version scanned every cmdline argument's basename
    and false-matched a Python one-liner that merely mentioned this
    function's own name in its source text - matching only comm and argv[0]
    avoids that class of false positive entirely.
    """
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return False

    for process_dir in proc_dir.iterdir():
        if not process_dir.name.isdigit():
            continue
        try:
            comm = (process_dir / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except (OSError, PermissionError):
            comm = ""
        if comm and _looks_like_lm_studio(comm):
            return True

        try:
            arguments = (process_dir / "cmdline").read_bytes().split(b"\0")
        except (OSError, PermissionError):
            continue
        if arguments and arguments[0]:
            executable_name = Path(os.fsdecode(arguments[0])).name
            if _looks_like_lm_studio(executable_name):
                return True

    return False


def _clear_stale_lm_studio_lock() -> list[str]:
    """Remove LM Studio's lock files, but only if nothing is actually running.

    Linux only - Windows uses an OS-level named mutex rather than a lock
    file we could safely delete, and macOS's exact lock path was never
    confirmed against real hardware, so this deliberately does nothing on
    either rather than guess. Never deletes anything unless a live process
    scan finds zero LM Studio processes - see _lm_studio_process_running.
    """
    if not sys.platform.startswith("linux"):
        return []

    if _lm_studio_process_running():
        return []

    removed: list[str] = []
    for lock_path in LM_STUDIO_LOCK_PATHS:
        # SingletonLock is a symlink (to a "host-pid" marker, not a real
        # file); Path.exists() follows symlinks and reports False for a
        # dangling one, so check is_symlink() too or a stale lock is missed.
        if not (lock_path.exists() or lock_path.is_symlink()):
            continue
        try:
            lock_path.unlink()
        except OSError:
            continue
        removed.append(str(lock_path))

    return removed


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
