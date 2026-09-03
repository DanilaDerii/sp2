"""Student runtime MCP tools."""

from __future__ import annotations

from typing import Any

from integrations.lm_studio_mcp.client import request_backend_json
from integrations.lm_studio_mcp.validators import (
    positive_int,
    required_text,
    without_none_values,
)


def register_student_tools(mcp: Any) -> None:
    """Register student runtime tools on a FastMCP server."""

    @mcp.tool()
    def sp2_list_packs(pack_id: str | None = None, active_only: bool = False) -> dict[str, Any]:
        """List course packs installed in the local SP2 student runtime.

        Args:
            pack_id: Optional logical pack id filter.
            active_only: When true, only return active installed packs.
        """
        params = without_none_values(
            {
                "pack_id": pack_id,
                "active_only": active_only,
            }
        )
        packs = request_backend_json("GET", "/packs", params=params)
        if not isinstance(packs, list):
            raise RuntimeError("SP2 backend API /packs response was not a list")

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
        resolved_installed_pack_id = positive_int(installed_pack_id, "installed_pack_id")

        pack = request_backend_json("GET", f"/packs/{resolved_installed_pack_id}")
        if not isinstance(pack, dict):
            raise RuntimeError(
                "SP2 backend API /packs/{installed_pack_id} response was not an object"
            )

        return {
            "mode": "installed_pack",
            "pack": pack,
        }

    @mcp.tool()
    def sp2_get_course_context(
        pack: int,
        question: str,
    ) -> dict[str, Any]:
        """Return course-pack retrieval context for one student question.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools.
            question: Student question to retrieve course context for.
        """
        resolved_installed_pack_id = positive_int(pack, "pack")
        normalized_question = required_text(
            question,
            "question",
            normalize_whitespace=True,
        )

        payload = without_none_values(
            {
                "installed_pack_id": resolved_installed_pack_id,
                "question": normalized_question,
            }
        )
        packet = request_backend_json("POST", "/retrieval/context", json_body=payload)
        if not isinstance(packet, dict):
            raise RuntimeError("SP2 backend API /retrieval/context response was not an object")

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
        normalized_path = required_text(pack_zip_path, "pack_zip_path")

        imported_pack = request_backend_json(
            "POST",
            "/packs/import-path",
            json_body={"pack_zip_path": normalized_path},
        )
        if not isinstance(imported_pack, dict):
            raise RuntimeError("SP2 backend API /packs/import-path response was not an object")

        return {
            "mode": "pack_imported",
            "imported_pack": imported_pack,
        }

    @mcp.tool()
    def sp2_delete_pack(pack: int) -> dict[str, Any]:
        """Delete one installed SP2 course pack by local installed pack id.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools.
        """
        resolved_installed_pack_id = positive_int(pack, "pack")

        deleted_pack = request_backend_json("DELETE", f"/packs/{resolved_installed_pack_id}")
        if not isinstance(deleted_pack, dict):
            raise RuntimeError("SP2 backend API delete-pack response was not an object")

        return {
            "mode": "pack_deleted",
            "deleted_pack": deleted_pack,
        }
