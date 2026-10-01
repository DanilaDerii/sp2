"""Teacher workflow MCP tools."""

from __future__ import annotations

from typing import Any

from integrations.backend_api import request_backend_json
from integrations.lm_studio_mcp.validators import required_text


def register_teacher_tools(mcp: Any) -> None:
    """Register the single course installation tool."""

    @mcp.tool()
    def sp2_ingest_source(source_path: str) -> dict[str, Any]:
        """Build or install a course from one local path.

        The backend decides what to do with the path. A PDF, ODT, DOCX, PPTX,
        or directory is built into a pack and installed. An SP2 ZIP pack is
        installed directly.

        Args:
            source_path: Absolute or user-expanded path to course material or
                an exported SP2 ZIP pack.
        """
        normalized_path = required_text(source_path, "source_path")
        result = request_backend_json(
            "POST",
            "/ingest/source",
            json_body={"source_path": normalized_path},
        )
        if not isinstance(result, dict):
            raise RuntimeError("SP2 backend API /ingest/source response was not an object")

        pack_id = result.get("pack_id")
        installed_pack_id = result.get("installed_pack_id")
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise RuntimeError("SP2 install response did not include pack_id")
        if not isinstance(installed_pack_id, int):
            raise RuntimeError("SP2 install response did not include installed_pack_id")

        return {
            "sp2_tool": "sp2_ingest_source",
            "mode": "course_pack_ready",
            "message": (
                f"Course pack {pack_id!r} is ready. Its installed_pack_id is "
                f"{installed_pack_id}."
            ),
            **result,
            "next_tool": "sp2_get_course_context",
        }
