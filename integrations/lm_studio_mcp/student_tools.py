"""Student runtime MCP tools."""

from __future__ import annotations

from typing import Any

from config.arguments import COURSE_ANSWER_GUIDANCE
from integrations.lm_studio_mcp.client import request_backend_json
from integrations.lm_studio_mcp.validators import (
    positive_int,
    required_text,
    without_none_values,
)


def _resolve_pack(pack: int | str, field_name: str) -> int:
    """Resolve a pack argument to a local installed pack id.

    Accepts the numeric installed pack id, and also the logical pack_id
    string (e.g. "music"). Models routinely reach for the latter, because
    sp2_list_packs returns both `id` and `pack_id` and the parameter is
    named "pack" - so accepting only the number turns a reasonable guess
    into a dead end.
    """
    text = str(pack).strip()
    if text.lstrip("+-").isdigit():
        return positive_int(text, field_name)

    name = required_text(text, field_name)
    matches = request_backend_json("GET", "/packs", params={"pack_id": name})
    if not isinstance(matches, list) or not matches:
        raise ValueError(
            f"No installed pack matches {field_name}={name!r}. "
            "Call sp2_list_packs and use a listed id or pack_id."
        )

    # Several installs can share one pack_id (e.g. re-imported versions).
    # Prefer an active pack, then the most recently installed.
    active = [pack_row for pack_row in matches if pack_row.get("is_active")]
    chosen = max(active or matches, key=lambda pack_row: int(pack_row.get("id", 0)))
    return positive_int(chosen["id"], field_name)


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
    def sp2_get_pack(installed_pack_id: int | str) -> dict[str, Any]:
        """Return one installed course pack by local SP2 installed pack id.

        Args:
            installed_pack_id: Local SQLite installed_packs.id value (e.g. 1).
                Also accepts a numeric string ("1") or the logical pack_id
                string shown by sp2_list_packs (e.g. "music").
        """
        resolved_installed_pack_id = _resolve_pack(installed_pack_id, "installed_pack_id")

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
        pack: int | str,
        question: str,
    ) -> dict[str, Any]:
        """Return course-pack retrieval context for one student question.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools
                (e.g. 1). Also accepts a numeric string ("1") or the
                logical pack_id string shown by sp2_list_packs ("music").
            question: Student question to retrieve course context for.
        """
        resolved_installed_pack_id = _resolve_pack(pack, "pack")
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
            "answer_guidance": COURSE_ANSWER_GUIDANCE,
            "packet": packet,
        }

    @mcp.tool()
    def sp2_get_file_summary_context(
        pack: int | str,
        source_id: str,
    ) -> dict[str, Any]:
        """Return every chunk from one source file for LM Studio to summarize.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools.
                Also accepts a numeric string or logical pack_id name.
            source_id: Exact source_id stored for the file inside the pack.
        """
        resolved_installed_pack_id = _resolve_pack(pack, "pack")
        normalized_source_id = required_text(source_id, "source_id")

        packet = request_backend_json(
            "POST",
            "/summaries/file-context",
            json_body={
                "installed_pack_id": resolved_installed_pack_id,
                "source_id": normalized_source_id,
            },
        )
        if not isinstance(packet, dict):
            raise RuntimeError(
                "SP2 backend API /summaries/file-context response was not an object"
            )

        return {
            "sp2_tool": "sp2_get_file_summary_context",
            "tool_role": "summary_context_only",
            "summary_scope": "file",
            "final_answer_owner": "LM Studio",
            "instruction": "Read every returned chunk and write the requested file summary.",
            "packet": packet,
        }

    @mcp.tool()
    def sp2_get_pack_summary_context(
        pack: int | str,
    ) -> dict[str, Any]:
        """Return every chunk from an installed pack for LM Studio to summarize.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools.
                Also accepts a numeric string or logical pack_id name.
        """
        resolved_installed_pack_id = _resolve_pack(pack, "pack")

        packet = request_backend_json(
            "POST",
            "/summaries/pack-context",
            json_body={"installed_pack_id": resolved_installed_pack_id},
        )
        if not isinstance(packet, dict):
            raise RuntimeError(
                "SP2 backend API /summaries/pack-context response was not an object"
            )

        return {
            "sp2_tool": "sp2_get_pack_summary_context",
            "tool_role": "summary_context_only",
            "summary_scope": "pack",
            "final_answer_owner": "LM Studio",
            "instruction": "Read every returned chunk and write the requested pack summary.",
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
    def sp2_delete_pack(pack: int | str) -> dict[str, Any]:
        """Delete one installed SP2 course pack by local installed pack id.

        Args:
            pack: Local SP2 installed pack id, as a number or numeric
                string. Unlike the read-only tools this does NOT accept a
                pack_id name, so a deletion always names exactly one
                installed pack.
        """
        resolved_installed_pack_id = positive_int(pack, "pack")

        deleted_pack = request_backend_json("DELETE", f"/packs/{resolved_installed_pack_id}")
        if not isinstance(deleted_pack, dict):
            raise RuntimeError("SP2 backend API delete-pack response was not an object")

        return {
            "mode": "pack_deleted",
            "deleted_pack": deleted_pack,
        }
