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

    Accepts the installed pack id and the pack name, the latter matched
    case-insensitively: pack ids are lowercase slugs, but a model naming the
    course from the question keeps the original capitalisation ("CSX4213"
    for "csx4213"). Both are checked against what is actually installed, so
    a model that skipped sp2_list_packs and guessed gets a message naming
    the real packs rather than a bare 404.
    """
    text = str(pack).strip()
    installed = request_backend_json("GET", "/packs")
    if not isinstance(installed, list):
        installed = []

    if text.lstrip("+-").isdigit():
        wanted_id = positive_int(text, field_name)
        matches = [row for row in installed if row.get("id") == wanted_id]
    else:
        wanted_name = required_text(text, field_name).casefold()
        matches = [
            row for row in installed
            if str(row.get("pack_id", "")).casefold() == wanted_name
        ]

    if not matches:
        names = ", ".join(sorted(str(row.get("pack_id")) for row in installed))
        raise ValueError(
            f"No installed pack matches {field_name}={text!r}. "
            f"Installed packs: {names or 'none'}. Call sp2_list_packs for details."
        )

    # Several installs can share one pack_id (e.g. re-imported versions).
    # Prefer an active pack, then the most recently installed.
    active = [row for row in matches if row.get("is_active")]
    chosen = max(active or matches, key=lambda row: int(row.get("id", 0)))
    return positive_int(chosen["id"], field_name)


def _pack_summary(pack_row: dict[str, Any]) -> dict[str, Any]:
    """Present one installed pack name-first.

    The numeric id is a SQLite AUTOINCREMENT key, kept because deletions must
    name exactly one install and because LanceDB chunks are keyed by it. It is
    never reused, so after deleting packs the remaining numbers have gaps -
    which reads like a bug when the id is shown as though it were the pack's
    position. Leading with the name avoids that.
    """
    summary = {
        "pack": pack_row.get("pack_id"),
        "title": pack_row.get("title"),
        "version": pack_row.get("version"),
        "is_active": pack_row.get("is_active"),
        "installed_at": pack_row.get("installed_at"),
        "installed_pack_id": pack_row.get("id"),
    }
    return {key: value for key, value in summary.items() if value is not None}


def register_student_tools(mcp: Any) -> None:
    """Register student runtime tools on a FastMCP server."""

    @mcp.tool()
    def sp2_list_packs(pack_id: str | None = None, active_only: bool = False) -> dict[str, Any]:
        """List course packs installed in the local SP2 student runtime.

        Each pack is identified by name (e.g. "csx4213"). Use that name for
        the other tools. installed_pack_id is an internal key with gaps; do
        not present it to the student as a pack number.

        Args:
            pack_id: Optional pack name filter.
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
            "packs": [_pack_summary(pack_row) for pack_row in packs],
            "note": (
                "Refer to packs by name (the pack field). installed_pack_id is an "
                "internal database key: it is never reused, so the numbers have gaps "
                "after a pack is deleted and do not indicate position or order."
            ),
        }

    @mcp.tool()
    def sp2_get_pack(installed_pack_id: int | str) -> dict[str, Any]:
        """Return one installed course pack.

        Args:
            installed_pack_id: The pack name shown by sp2_list_packs
                (e.g. "music"). The internal installed_pack_id number is
                also accepted, as an int or a numeric string.
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
            pack: The pack name shown by sp2_list_packs (e.g. "music").
                The internal installed_pack_id number is also accepted.
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
        """Return an overview of an installed pack for LM Studio to summarize.

        Returns only the opening chunks of each source file, not the full
        content. For a specific question use sp2_get_course_context; for the
        complete content of one file use sp2_get_file_summary_context.

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
            "instruction": "These are the opening chunks of each file, not the full pack. Write an overview and say it is based on the start of each file.",
            "packet": packet,
        }

    @mcp.tool()
    def sp2_import_pack_from_path(pack_zip_path: str) -> dict[str, Any]:
        """Import a teacher-exported SP2 pack zip from a local filesystem path.

        If a pack with the same logical pack_id is already installed, this
        updates it in place (the previous install is replaced) instead of
        failing - there's no separate "update" tool or delete-first step.

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

        replaced_installed_pack_ids = imported_pack.get("replaced_installed_pack_ids") or []
        if replaced_installed_pack_ids:
            return {
                "mode": "pack_updated",
                "imported_pack": imported_pack,
                "message": (
                    "This pack was already installed, so it was updated in place. "
                    f"Replaced previous install(s): {replaced_installed_pack_ids}."
                ),
            }

        return {
            "mode": "pack_imported",
            "imported_pack": imported_pack,
        }

    @mcp.tool()
    def sp2_update_pack(pack: int | str) -> dict[str, Any]:
        """Update an installed SP2 course pack - no file path needed.

        Looks for the newest exported zip next to wherever this pack was
        last imported from (every teacher/student has a different folder
        layout, so this is learned from their own prior import, not
        assumed) and re-imports it in place. Use this when a student asks
        to update/refresh a course pack without giving a path.

        If this fails (e.g. the pack was never imported with a path, or no
        newer export can be found in that folder), fall back to
        sp2_import_pack_from_path with an explicit path.

        Args:
            pack: Local SP2 installed pack id returned by SP2 pack tools
                (e.g. 1). Also accepts a numeric string ("1") or the
                logical pack_id string shown by sp2_list_packs ("music").
        """
        resolved_installed_pack_id = _resolve_pack(pack, "pack")

        imported_pack = request_backend_json(
            "POST", f"/packs/{resolved_installed_pack_id}/update"
        )
        if not isinstance(imported_pack, dict):
            raise RuntimeError("SP2 backend API /packs/{id}/update response was not an object")

        new_installed_pack_id = (imported_pack.get("installed_pack") or {}).get("id")
        replaced_installed_pack_ids = imported_pack.get("replaced_installed_pack_ids") or []

        return {
            "mode": "pack_updated",
            "imported_pack": imported_pack,
            "message": (
                f"Found a newer export automatically and updated the pack. "
                f"New installed pack id: {new_installed_pack_id}. "
                f"Replaced previous install(s): {replaced_installed_pack_ids}."
            ),
        }

    @mcp.tool()
    def sp2_delete_pack(pack: int | str) -> dict[str, Any]:
        """Delete one installed SP2 course pack by local installed pack id.

        Args:
            pack: The internal installed_pack_id number shown by
                sp2_list_packs, as a number or numeric string. Unlike the
                read-only tools this does NOT accept a pack name, so a
                deletion always names exactly one installed pack even when
                several installs share a name.
        """
        resolved_installed_pack_id = positive_int(pack, "pack")

        deleted_pack = request_backend_json("DELETE", f"/packs/{resolved_installed_pack_id}")
        if not isinstance(deleted_pack, dict):
            raise RuntimeError("SP2 backend API delete-pack response was not an object")

        return {
            "mode": "pack_deleted",
            "deleted_pack": deleted_pack,
        }
