"""HTTP client helpers for the SP2 backend API."""

from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_BACKEND_API_BASE_URL = "http://127.0.0.1:8001"
BACKEND_API_BASE_URL_ENV = "SP2_BACKEND_API_BASE_URL"
BACKEND_START_HINT = (
    "environment/.venv/bin/python -m uvicorn "
    "backend.api.api:app --host 127.0.0.1 --port 8001"
)
HTTP_TIMEOUT_SECONDS = 120.0


def _api_base_url(env_name: str, default_url: str) -> str:
    base_url = os.environ.get(env_name, default_url)
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise RuntimeError(f"{env_name} must not be empty")
    return normalized_base_url


def _api_url(base_url: str, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base_url}{path}"


def backend_api_url(path: str) -> str:
    """Return an absolute URL for an SP2 backend API path."""
    base_url = _api_base_url(BACKEND_API_BASE_URL_ENV, DEFAULT_BACKEND_API_BASE_URL)
    return _api_url(base_url, path)


def _api_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or response.reason_phrase

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is not None:
            return str(detail)
    return str(payload)


def _request_json(
    url: str,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, params=params, json=json_body)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not connect to the SP2 backend API. Start it with: {BACKEND_START_HINT}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"SP2 backend API request timed out: {method} {path}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"SP2 backend API request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = _api_error_detail(response)
        raise RuntimeError(
            f"SP2 backend API returned HTTP {response.status_code} "
            f"for {method} {path}: {detail}"
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"SP2 backend API returned invalid JSON for {method} {path}") from exc


def request_backend_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    """Request JSON from the unified SP2 backend API."""
    return _request_json(
        backend_api_url(path),
        method,
        path,
        params=params,
        json_body=json_body,
    )
