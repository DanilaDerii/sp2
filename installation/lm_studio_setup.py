"""Download, load, and verify SP2's required LM Studio models."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from config.arguments import (
    DEFAULT_EMBEDDING_DIM,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_MODEL_DOWNLOAD,
    DEFAULT_EMBEDDING_MODEL_KEY,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_MODEL_DOWNLOAD,
    DEFAULT_LLM_MODEL_KEY,
    DEFAULT_LM_STUDIO_BASE_URL,
)
from installation.setup_helpers import SetupError, _ok, _print_step, _run


LM_STUDIO_SERVER_WAIT_SECONDS = 30


def _find_lms() -> str:
    lms_path = shutil.which("lms")
    if lms_path is None:
        executable_name = "lms.exe" if os.name == "nt" else "lms"
        bundled_lms = Path.home() / ".lmstudio" / "bin" / executable_name
        if bundled_lms.is_file():
            lms_path = str(bundled_lms)

    if lms_path is None:
        raise SetupError(
            "LM Studio's 'lms' command was not found. Install LM Studio, open it "
            "once, then restart this terminal and run setup again. SP2 checked "
            "both PATH and LM Studio's .lmstudio/bin directory."
        )

    version = _run([lms_path, "--version"], capture_output=True)
    version_text = (version.stdout or version.stderr).strip()
    _ok(f"LM Studio CLI is available: {version_text or lms_path}")
    return lms_path


def _download_models(lms_path: str) -> None:
    _print_step("Downloading the LM Studio embedding model")
    print(f"Model: {DEFAULT_EMBEDDING_MODEL_DOWNLOAD}")
    _run(
        [
            lms_path,
            "get",
            DEFAULT_EMBEDDING_MODEL_DOWNLOAD,
            "--gguf",
            "--yes",
        ]
    )
    _ok("Embedding model is downloaded")

    _print_step("Downloading the LM Studio chat model")
    print(f"Model: {DEFAULT_LLM_MODEL_DOWNLOAD}")
    print("This GGUF download is approximately 4.7 GB.")
    _run(
        [lms_path, "get", DEFAULT_LLM_MODEL_DOWNLOAD, "--gguf", "--yes"]
    )
    _ok("Chat model is downloaded")


def _lm_studio_url(path: str) -> str:
    return f"{DEFAULT_LM_STUDIO_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def _lm_studio_native_url(path: str) -> str:
    server_root = DEFAULT_LM_STUDIO_BASE_URL.removesuffix("/v1")
    return f"{server_root.rstrip('/')}/api/v1/{path.lstrip('/')}"


def _server_is_ready() -> bool:
    request = Request(_lm_studio_url("models"), method="GET")
    try:
        with urlopen(request, timeout=2) as response:
            return 200 <= response.status < 300
    except HTTPError as exc:
        if exc.code in {401, 403}:
            raise SetupError(
                "LM Studio authentication is enabled, but SP2 has no API token "
                "configured. Disable authentication for the local server and retry."
            ) from exc
        return False
    except (OSError, URLError):
        return False


def _stop_lm_studio_server(lms_path: str) -> None:
    try:
        _run([lms_path, "server", "stop"])
    except SetupError as exc:
        print(f"[warning] Could not stop the LM Studio server: {exc}")
    else:
        _ok("Stopped the LM Studio server after setup failure")


def _ensure_lm_studio_server(lms_path: str) -> bool:
    _print_step("Checking the LM Studio server")
    if _server_is_ready():
        _ok(f"LM Studio server is ready at {DEFAULT_LM_STUDIO_BASE_URL}")
        return False

    print("LM Studio server is not reachable; starting it now.")
    _run([lms_path, "server", "start"])
    try:
        deadline = time.monotonic() + LM_STUDIO_SERVER_WAIT_SECONDS
        while time.monotonic() < deadline:
            if _server_is_ready():
                _ok(f"LM Studio server is ready at {DEFAULT_LM_STUDIO_BASE_URL}")
                return True
            time.sleep(1)

        raise SetupError(
            "LM Studio server did not become ready within "
            f"{LM_STUDIO_SERVER_WAIT_SECONDS} seconds"
        )
    except (SetupError, KeyboardInterrupt):
        _stop_lm_studio_server(lms_path)
        raise


def _loaded_model_ids() -> set[str]:
    request = Request(_lm_studio_native_url("models"), method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (
        HTTPError,
        URLError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise SetupError(f"Could not list loaded LM Studio models: {exc}") from exc

    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list):
        raise SetupError("LM Studio /api/v1/models returned an unexpected response")

    identifiers: set[str] = set()
    for model in raw_models:
        instances = model.get("loaded_instances") if isinstance(model, dict) else None
        if not isinstance(instances, list):
            continue
        identifiers.update(
            instance["id"]
            for instance in instances
            if isinstance(instance, dict) and isinstance(instance.get("id"), str)
        )
    return identifiers


def _load_embedding_model(lms_path: str) -> None:
    _print_step("Loading the LM Studio embedding model")
    if DEFAULT_EMBEDDING_MODEL in _loaded_model_ids():
        _ok(f"Embedding model is already loaded as: {DEFAULT_EMBEDDING_MODEL}")
        return

    _run(
        [
            lms_path,
            "load",
            DEFAULT_EMBEDDING_MODEL_KEY,
            "--identifier",
            DEFAULT_EMBEDDING_MODEL,
            "--yes",
        ]
    )
    _ok(f"Embedding model loaded as: {DEFAULT_EMBEDDING_MODEL}")


def _load_chat_model(lms_path: str) -> None:
    _print_step("Loading the LM Studio chat model")
    if DEFAULT_LLM_MODEL in _loaded_model_ids():
        _ok(f"Chat model is already loaded as: {DEFAULT_LLM_MODEL}")
        return

    _run(
        [
            lms_path,
            "load",
            DEFAULT_LLM_MODEL_KEY,
            "--identifier",
            DEFAULT_LLM_MODEL,
            "--yes",
        ]
    )
    _ok(f"Chat model loaded as: {DEFAULT_LLM_MODEL}")


def _embedding_vector() -> list[Any]:
    body = json.dumps(
        {
            "model": DEFAULT_EMBEDDING_MODEL,
            "input": "search_query: SP2 setup verification",
        }
    ).encode("utf-8")
    request = Request(
        _lm_studio_url("embeddings"),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise SetupError(
            f"LM Studio embedding verification failed with HTTP {exc.code}: {detail}"
        ) from exc
    except (URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SetupError(f"LM Studio embedding verification failed: {exc}") from exc

    data = payload.get("data") if isinstance(payload, dict) else None
    first = data[0] if isinstance(data, list) and data else None
    vector = first.get("embedding") if isinstance(first, dict) else None
    if not isinstance(vector, list):
        raise SetupError("LM Studio embedding response did not contain a vector")
    return vector


def _verify_embedding_model() -> None:
    _print_step("Verifying the LM Studio embedding model")
    vector = _embedding_vector()
    if len(vector) != DEFAULT_EMBEDDING_DIM:
        raise SetupError(
            "LM Studio returned the wrong embedding dimension: "
            f"expected={DEFAULT_EMBEDDING_DIM}, actual={len(vector)}"
        )
    _ok(
        f"Embedding API returned the expected {DEFAULT_EMBEDDING_DIM}-dimensional vector"
    )


def _setup_lm_studio(lms_path: str) -> None:
    _download_models(lms_path)
    server_started_by_setup = _ensure_lm_studio_server(lms_path)
    try:
        _load_embedding_model(lms_path)
        _verify_embedding_model()
        _load_chat_model(lms_path)
    except (SetupError, KeyboardInterrupt):
        if server_started_by_setup:
            _stop_lm_studio_server(lms_path)
        raise
