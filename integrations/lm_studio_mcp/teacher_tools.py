"""Teacher workflow MCP tools."""

from __future__ import annotations

from typing import Any

from integrations.lm_studio_mcp.client import request_student_json, request_teacher_json
from integrations.lm_studio_mcp.validators import required_text


def register_teacher_tools(mcp: Any) -> None:
    """Register teacher workflow tools on a FastMCP server."""

    @mcp.tool()
    def sp2_ingest_pdf_from_path(pdf_path: str) -> dict[str, Any]:
        """Build a teacher pack from a PDF and import it into student storage.

        Args:
            pdf_path: Absolute or user-expanded path to a local teacher PDF file.
        """
        normalized_path = required_text(pdf_path, "pdf_path")

        teacher_ingest = request_teacher_json(
            "POST",
            "/ingest/pdf-path",
            json_body={"pdf_path": normalized_path},
        )
        if not isinstance(teacher_ingest, dict):
            raise RuntimeError(
                "SP2 teacher API /ingest/pdf-path response was not an object"
            )

        zip_path = teacher_ingest.get("zip_path")
        if not isinstance(zip_path, str) or not zip_path.strip():
            raise RuntimeError(
                "SP2 teacher ingest response did not include a usable zip_path"
            )

        imported_pack = request_student_json(
            "POST",
            "/packs/import-path",
            json_body={"pack_zip_path": zip_path},
        )
        if not isinstance(imported_pack, dict):
            raise RuntimeError(
                "SP2 student API /packs/import-path response was not an object"
            )

        installed_pack = imported_pack.get("installed_pack")
        if not isinstance(installed_pack, dict):
            raise RuntimeError("SP2 student import response did not include installed_pack")

        installed_pack_id = installed_pack.get("id")
        pack_id = installed_pack.get("pack_id")
        title = installed_pack.get("title")
        chunk_count = imported_pack.get("chunk_count")

        if not isinstance(installed_pack_id, int):
            raise RuntimeError(
                "SP2 student import response did not include installed_pack.id"
            )
        if not isinstance(pack_id, str) or not pack_id.strip():
            raise RuntimeError(
                "SP2 student import response did not include installed_pack.pack_id"
            )
        if not isinstance(title, str) or not title.strip():
            raise RuntimeError(
                "SP2 student import response did not include installed_pack.title"
            )
        if not isinstance(chunk_count, int):
            raise RuntimeError("SP2 student import response did not include chunk_count")

        return {
            "sp2_tool": "sp2_ingest_pdf_from_path",
            "mode": "course_pack_ready",
            "message": (
                "Course pack is ready. "
                f"Use installed_pack_id={installed_pack_id} for retrieval."
            ),
            "installed_pack_id": installed_pack_id,
            "pack_id": pack_id,
            "title": title,
            "chunk_count": chunk_count,
            "zip_path": zip_path,
            "install_path": imported_pack.get("install_path"),
            "embedding_model": installed_pack.get("embedding_model"),
            "embedding_dim": installed_pack.get("embedding_dim"),
            "next_tool": "sp2_get_course_context",
        }
