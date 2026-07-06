"""Guided first-run setup for the local SP2 runtime."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / "environment" / ".venv"
REQUIREMENTS_PATH = REPO_ROOT / "environment" / "requirements.txt"
MCP_SERVER_PATH = REPO_ROOT / "integrations" / "lm_studio_mcp" / "server.py"
DEFAULT_LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"
DEFAULT_EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"
EXPECTED_EMBEDDING_DIM = 768
STUDENT_API_BASE_URL = "http://127.0.0.1:8001"
TEACHER_API_BASE_URL = "http://127.0.0.1:8002"


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


def _warn(message: str) -> None:
    print(f"[warn] {message}")


def _run(command: list[str], *, cwd: Path = REPO_ROOT, timeout: int | None = None) -> None:
    completed = subprocess.run(command, cwd=cwd, timeout=timeout, check=False)
    if completed.returncode != 0:
        raise SetupError(f"Command failed with exit code {completed.returncode}: {' '.join(command)}")


def _create_venv() -> Path:
    _print_step("Creating root virtual environment")
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
    _print_step("Installing Python requirements")
    if not REQUIREMENTS_PATH.is_file():
        raise SetupError(f"Requirements file not found: {REQUIREMENTS_PATH}")
    _run([str(python_path), "-m", "pip", "install", "-r", str(REQUIREMENTS_PATH)])
    _ok(f"Installed requirements from: {REQUIREMENTS_PATH}")


def _initialize_storage(python_path: Path) -> None:
    _print_step("Initializing student storage")
    _run([str(python_path), "-m", "student.storage.database.setup.create_sqlite_db"])
    _ok("SQLite database is ready")
    _run([str(python_path), "-m", "student.storage.database.setup.create_lancedb_db"])
    _ok("LanceDB table is ready")


def _request_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> Any:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:
        raw_body = response.read().decode("utf-8")
    return json.loads(raw_body)


def _check_lm_studio(base_url: str, model: str) -> None:
    _print_step("Checking LM Studio local embedding API")
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise SetupError("LM Studio base URL must not be empty")

    try:
        _request_json(f"{normalized_base_url}/models", timeout=5.0)
        _ok(f"LM Studio server is reachable: {normalized_base_url}")
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        _warn(
            "LM Studio server is not reachable yet. Start LM Studio's local server "
            f"and rerun this script to validate embeddings. Detail: {exc}"
        )
        return

    try:
        payload = _request_json(
            f"{normalized_base_url}/embeddings",
            method="POST",
            body={"model": model, "input": "software testing"},
            timeout=30.0,
        )
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        _warn(
            "LM Studio responded, but the embedding test failed. Make sure the "
            f"model is downloaded/loaded: {model}. Detail: {exc}"
        )
        return

    try:
        vector = payload["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError):
        _warn("LM Studio embedding response did not use the expected OpenAI-compatible shape")
        return

    if not isinstance(vector, list):
        _warn("LM Studio embedding field was not a JSON array")
        return

    vector_dim = len(vector)
    if vector_dim != EXPECTED_EMBEDDING_DIM:
        _warn(f"Embedding dimension is {vector_dim}, expected {EXPECTED_EMBEDDING_DIM}")
        return

    _ok(f"Embedding model works: {model}")
    _ok(f"Embedding dimension is {EXPECTED_EMBEDDING_DIM}")


def _backend_health() -> bool:
    try:
        payload = _request_json(f"{STUDENT_API_BASE_URL}/health", timeout=2.0)
    except Exception:
        return False
    return isinstance(payload, dict) and payload.get("status") == "ok"


def _verify_backend(python_path: Path) -> None:
    _print_step("Starting SP2 student backend for a health check")
    if _backend_health():
        _ok(f"Backend is already running: {STUDENT_API_BASE_URL}")
        _warn("This setup script did not start that existing backend, so it will not stop it")
        return

    process = subprocess.Popen(
        [
            str(python_path),
            "-m",
            "uvicorn",
            "student.backend.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise SetupError("Backend process exited before /health became ready")
            if _backend_health():
                _ok(f"Backend health check passed: {STUDENT_API_BASE_URL}/health")
                return
            time.sleep(1)
        raise SetupError("Backend did not become healthy within 30 seconds")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            _ok("Stopped the temporary backend process started by setup")


def _mcp_config(python_path: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            "sp2-course-context": {
                "command": str(python_path),
                "args": [str(MCP_SERVER_PATH)],
                "env": {
                    "SP2_STUDENT_API_BASE_URL": STUDENT_API_BASE_URL,
                    "SP2_TEACHER_API_BASE_URL": TEACHER_API_BASE_URL,
                },
            }
        }
    }


def _print_final_instructions(python_path: Path) -> None:
    start_command = (
        f"cd {REPO_ROOT}\n"
        f"{python_path} -m uvicorn student.backend.app:app --host 127.0.0.1 --port 8001"
    )
    teacher_start_command = (
        f"cd {REPO_ROOT}\n"
        f"{python_path} -m uvicorn teacher.backend.app:app --host 127.0.0.1 --port 8002"
    )

    _print_step("LM Studio MCP config")
    print("Paste this JSON into LM Studio's MCP/server configuration:")
    print(json.dumps(_mcp_config(python_path), indent=2))

    _print_step("Student backend command")
    print("Copy this command when you want to start the SP2 student backend:")
    print()
    print(start_command)
    print()
    print("To stop the backend afterward, press Ctrl+C in the terminal running it.")

    _print_step("Teacher backend command")
    print("Start this in a second terminal when using teacher ingest MCP tools:")
    print()
    print(teacher_start_command)
    print()
    print("To stop the backend afterward, press Ctrl+C in the terminal running it.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Set up and validate the local SP2 runtime.")
    parser.add_argument(
        "--lm-studio-base-url",
        default=DEFAULT_LM_STUDIO_BASE_URL,
        help=f"LM Studio OpenAI-compatible base URL. Default: {DEFAULT_LM_STUDIO_BASE_URL}",
    )
    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"Embedding model to validate. Default: {DEFAULT_EMBEDDING_MODEL}",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    print("SP2 installation setup")
    print(f"Repo root: {REPO_ROOT}")

    try:
        python_path = _create_venv()
        _install_requirements(python_path)
        _initialize_storage(python_path)
        _check_lm_studio(args.lm_studio_base_url, args.embedding_model)
        _verify_backend(python_path)
        _print_final_instructions(python_path)
    except SetupError as exc:
        print()
        print(f"[error] {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("[error] Setup interrupted")
        return 130

    print()
    _ok("SP2 setup script finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
