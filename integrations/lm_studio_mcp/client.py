"""HTTP client helpers for SP2 backend APIs."""

from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_STUDENT_API_BASE_URL = "http://127.0.0.1:8001"
DEFAULT_TEACHER_API_BASE_URL = "http://127.0.0.1:8002"
STUDENT_API_BASE_URL_ENV = "SP2_STUDENT_API_BASE_URL"
TEACHER_API_BASE_URL_ENV = "SP2_TEACHER_API_BASE_URL"
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


def student_api_url(path: str) -> str:
    """Return an absolute URL for a student backend API path."""
    base_url = _api_base_url(STUDENT_API_BASE_URL_ENV, DEFAULT_STUDENT_API_BASE_URL)
    return _api_url(base_url, path)


def teacher_api_url(path: str) -> str:
    """Return an absolute URL for a teacher backend API path."""
    base_url = _api_base_url(TEACHER_API_BASE_URL_ENV, DEFAULT_TEACHER_API_BASE_URL)
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
    api_name: str,
    url: str,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    start_hint: str,
) -> Any:
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, params=params, json=json_body)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Could not connect to the SP2 {api_name} API. Start it with: {start_hint}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"SP2 {api_name} API request timed out: {method} {path}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"SP2 {api_name} API request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = _api_error_detail(response)
        raise RuntimeError(
            f"SP2 {api_name} API returned HTTP {response.status_code} "
            f"for {method} {path}: {detail}"
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"SP2 {api_name} API returned invalid JSON for {method} {path}") from exc


def request_student_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    """Request JSON from the SP2 student backend API."""
    return _request_json(
        "student",
        student_api_url(path),
        method,
        path,
        params=params,
        json_body=json_body,
        start_hint=(
            "environment/.venv/bin/python -m uvicorn "
            "student.backend.app:app --host 127.0.0.1 --port 8001"
        ),
    )


def request_teacher_json(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    """Request JSON from the SP2 teacher backend API."""
    return _request_json(
        "teacher",
        teacher_api_url(path),
        method,
        path,
        params=params,
        json_body=json_body,
        start_hint=(
            "environment/.venv/bin/python -m uvicorn "
            "teacher.backend.app:app --host 127.0.0.1 --port 8002"
        ),
    )
