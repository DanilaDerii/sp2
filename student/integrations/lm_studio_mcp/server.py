"""LM Studio MCP tools for the SP2 student runtime.

This server is intentionally a thin adapter over the existing student FastAPI
API. LM Studio owns the chat UI and final answer generation; SP2 only returns
pack metadata and retrieval context.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


DEFAULT_STUDENT_API_BASE_URL = "http://127.0.0.1:8001"
STUDENT_API_BASE_URL_ENV = "SP2_STUDENT_API_BASE_URL"
HTTP_TIMEOUT_SECONDS = 120.0


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


mcp = FastMCP(
    "sp2-course-context",
    instructions=(
        "Expose SP2 course-pack retrieval tools to LM Studio. "
        "These tools return structured context only; LM Studio writes final answers."
    ),
)


def _student_api_base_url() -> str:
    base_url = os.environ.get(STUDENT_API_BASE_URL_ENV, DEFAULT_STUDENT_API_BASE_URL)
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise RuntimeError(f"{STUDENT_API_BASE_URL_ENV} must not be empty")
    return normalized_base_url


def _student_api_url(path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{_student_api_base_url()}{path}"


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
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    url = _student_api_url(path)
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS) as client:
            response = client.request(method, url, params=params, json=json_body)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "Could not connect to the SP2 student API. "
            "Start it with: environment/.venv/bin/python -m uvicorn "
            "student.backend.app:app --host 127.0.0.1 --port 8001"
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"SP2 student API request timed out: {method} {path}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"SP2 student API request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = _api_error_detail(response)
        raise RuntimeError(
            f"SP2 student API returned HTTP {response.status_code} for {method} {path}: {detail}"
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"SP2 student API returned invalid JSON for {method} {path}") from exc


def _without_none_values(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}


@mcp.tool()
def sp2_list_packs(pack_id: str | None = None, active_only: bool = False) -> dict[str, Any]:
    """List course packs installed in the local SP2 student runtime.

    Args:
        pack_id: Optional logical pack id filter.
        active_only: When true, only return active installed packs.
    """
    params = _without_none_values(
        {
            "pack_id": pack_id,
            "active_only": active_only,
        }
    )
    packs = _request_json("GET", "/packs", params=params)
    if not isinstance(packs, list):
        raise RuntimeError("SP2 student API /packs response was not a list")

    return {
        "mode": "installed_packs",
        "count": len(packs),
        "packs": packs,
    }


@mcp.tool()
def sp2_get_pack(installed_pack_id: int) -> dict[str, Any]:
    """Return one installed course pack by local SP2 installed pack id.

    Args:
        installed_pack_id: Local SQLite installed_packs.id value.
    """
    if installed_pack_id <= 0:
        raise ValueError("installed_pack_id must be a positive integer")

    pack = _request_json("GET", f"/packs/{installed_pack_id}")
    if not isinstance(pack, dict):
        raise RuntimeError("SP2 student API /packs/{installed_pack_id} response was not an object")

    return {
        "mode": "installed_pack",
        "pack": pack,
    }


@mcp.tool()
def sp2_get_course_context(
    installed_pack_id: int,
    question: str,
    top_k: int | None = None,
    max_distance: float | None = None,
) -> dict[str, Any]:
    """Return course-pack retrieval context for one student question.

    Args:
        installed_pack_id: Local SQLite installed_packs.id value.
        question: Student question to retrieve course context for.
        top_k: Optional number of chunks to retrieve.
        max_distance: Optional LanceDB distance cutoff.
    """
    if installed_pack_id <= 0:
        raise ValueError("installed_pack_id must be a positive integer")

    normalized_question = " ".join(question.split()).strip()
    if not normalized_question:
        raise ValueError("question must not be empty")

    payload = _without_none_values(
        {
            "installed_pack_id": installed_pack_id,
            "question": normalized_question,
            "top_k": top_k,
            "max_distance": max_distance,
        }
    )
    packet = _request_json("POST", "/retrieval/context", json_body=payload)
    if not isinstance(packet, dict):
        raise RuntimeError("SP2 student API /retrieval/context response was not an object")

    return {
        "sp2_tool": "sp2_get_course_context",
        "tool_role": "retrieval_context_only",
        "final_answer_owner": "LM Studio",
        "packet": packet,
    }


@mcp.tool()
def sp2_import_pack_from_path(pack_zip_path: str) -> dict[str, Any]:
    """Import a teacher-exported SP2 pack zip from a local filesystem path.

    Args:
        pack_zip_path: Absolute or user-expanded path to a teacher-exported .zip pack.
    """
    normalized_path = pack_zip_path.strip()
    if not normalized_path:
        raise ValueError("pack_zip_path must not be empty")

    imported_pack = _request_json(
        "POST",
        "/packs/import-path",
        json_body={"pack_zip_path": normalized_path},
    )
    if not isinstance(imported_pack, dict):
        raise RuntimeError("SP2 student API /packs/import-path response was not an object")

    return {
        "mode": "pack_imported",
        "imported_pack": imported_pack,
    }


def main() -> None:
    logger.info("Starting SP2 LM Studio MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
