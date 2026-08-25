"""Download, load-swap, and size lookups for candidate chat models.

Reuses the lms CLI plumbing already built for first-run setup
(installation/lm_studio_setup.py, installation/setup_helpers.py) instead of
re-implementing subprocess/download handling.
"""

from __future__ import annotations

import json

from installation.lm_studio_setup import _find_lms, _loaded_model_ids
from installation.setup_helpers import SetupError, _ok, _print_step, _run


def find_lms() -> str:
    """Return the path to the lms CLI, raising SetupError if it is missing."""
    return _find_lms()


def ensure_model_downloaded(lms_path: str, download_url: str) -> None:
    """Download a GGUF model if it is not already on disk."""
    _print_step(f"Downloading model: {download_url}")
    _run([lms_path, "get", download_url, "--gguf", "--yes"])
    _ok(f"Model is downloaded: {download_url}")


def switch_to_model(
    lms_path: str,
    model_key: str,
    identifier: str,
    *,
    previous_identifier: str | None = None,
) -> None:
    """Unload the previous candidate chat model, then load the next one.

    Only unloads the specific previous chat model identifier (not
    ``--all``), so the embedding model stays loaded across the whole run -
    retrieval needs it to embed each question. Keeping just one chat model
    resident at a time still bounds peak memory, which matters on the
    low-RAM machines this harness exists to evaluate for.
    """
    _print_step(f"Switching to chat model: {identifier}")
    if previous_identifier is not None:
        _run([lms_path, "unload", previous_identifier])
    _run([lms_path, "load", model_key, "--identifier", identifier, "--yes"])

    if identifier not in _loaded_model_ids():
        raise SetupError(f"Model did not report as loaded after switch: {identifier}")
    _ok(f"Chat model loaded as: {identifier}")


def installed_model_sizes(lms_path: str) -> dict[str, int]:
    """Return {model_key: size_bytes} for every model already on disk."""
    completed = _run([lms_path, "ls", "--json"], capture_output=True)
    try:
        models = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise SetupError("Could not parse 'lms ls --json' output") from exc

    if not isinstance(models, list):
        raise SetupError("'lms ls --json' did not return a list")

    sizes: dict[str, int] = {}
    for model in models:
        if not isinstance(model, dict):
            continue
        model_key = model.get("modelKey")
        size_bytes = model.get("sizeBytes")
        if isinstance(model_key, str) and isinstance(size_bytes, int):
            sizes[model_key] = size_bytes
    return sizes
