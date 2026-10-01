"""Student runtime MCP tools."""

from __future__ import annotations

from typing import Any

from config.arguments import COURSE_ANSWER_GUIDANCE
from integrations.backend_api import request_backend_json
from integrations.lm_studio_mcp.validators import (
    positive_int,
    required_text,
    without_none_values,
)


_SOURCE_FILE_SUFFIXES = (".pdf", ".odt", ".docx", ".pptx")


def _pack_title_reference(value: object) -> str:
    """Normalize a pack title or single-source filename for comparison."""
    reference = str(value).strip().replace("\\", "/").rsplit("/", 1)[-1]
    folded_reference = reference.casefold()
    for suffix in _SOURCE_FILE_SUFFIXES:
        if folded_reference.endswith(suffix):
            reference = reference[: -len(suffix)]
            break
    return "".join(reference.casefold().split())


def _resolve_pack(pack: int | str, field_name: str) -> int:
    """Resolve a pack argument to a local installed pack id.

    Accepts the installed pack id, logical pack_id, displayed title, or the
    original filename for a single-file pack. Text matches are
    case- and whitespace-insensitive, and an optional supported source
    extension is ignored for title matching.
    """
    text = str(pack).strip()
    installed = request_backend_json("GET", "/packs")
    if not isinstance(installed, list):
        installed = []

    if text.lstrip("+-").isdigit():
        wanted_id = positive_int(text, field_name)
        matches = [row for row in installed if row.get("id") == wanted_id]
    else:
        wanted_text = required_text(text, field_name)
        exact_matches = [
            row for row in installed
            if str(row.get("pack_id", "")) == wanted_text
        ]
        wanted_name = "".join(wanted_text.casefold().split())
        matches = exact_matches or [
            row for row in installed
            if "".join(str(row.get("pack_id", "")).casefold().split()) == wanted_name
        ]
        if not matches:
            exact_title_matches = [
                row for row in installed
                if str(row.get("title", "")) == wanted_text
            ]
            matches = exact_title_matches or [
                row for row in installed
                if "".join(str(row.get("title", "")).casefold().split()) == wanted_name
            ]
        if not matches:
            wanted_title = _pack_title_reference(text)
            matches = [
                row for row in installed
                if _pack_title_reference(row.get("title", "")) == wanted_title
            ]

        matched_pack_ids = {
            "".join(str(row.get("pack_id", "")).casefold().split())
            for row in matches
        }
        if len(matched_pack_ids) > 1:
            choices = ", ".join(
                sorted(
                    f"{row.get('pack_id')} ({row.get('title')})"
                    for row in matches
                )
            )
            raise ValueError(
                f"More than one installed pack matches {field_name}={text!r}: "
                f"{choices}. Use the pack name from sp2_list_packs."
            )

    if not matches:
        names = ", ".join(
            sorted(
                f"{row.get('pack_id')} ({row.get('title')})"
                for row in installed
            )
        )
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
    """Present one installed pack with both stable and local identifiers.

    The numeric id is a SQLite AUTOINCREMENT key, kept because deletions must
    name exactly one install and because LanceDB chunks are keyed by it. It is
    never reused, so after deleting packs the remaining numbers can have gaps.
    """
    summary = {
        "pack_id": pack_row.get("pack_id"),
        "installed_pack_id": pack_row.get("id"),
        "title": pack_row.get("title"),
        "version": pack_row.get("version"),
        "is_active": pack_row.get("is_active"),
        "installed_at": pack_row.get("installed_at"),
    }
    return {key: value for key, value in summary.items() if value is not None}


def register_student_tools(mcp: Any) -> None:
    """Register student runtime tools on a FastMCP server."""

    @mcp.tool()
    def sp2_list_packs(pack_id: str | None = None, active_only: bool = False) -> dict[str, Any]:
        """List course packs installed in the local SP2 student runtime.

        Each result includes both pack_id (the logical name) and
        installed_pack_id (the local numeric id). Always show both identifiers
        to the student so either can be used in a later question. Other tools
        also accept the displayed title and, for single-file packs, the
        original filename.

        Args:
            pack_id: Optional pack name or title filter. Matching ignores case
                and whitespace.
            active_only: When true, only return active installed packs.
        """
        params = without_none_values(
            {
                "active_only": active_only,
            }
        )
        packs = request_backend_json("GET", "/packs", params=params)
        if not isinstance(packs, list):
            raise RuntimeError("SP2 backend API /packs response was not a list")
        if pack_id is not None:
            wanted = required_text(pack_id, "pack_id")
            wanted_key = "".join(wanted.casefold().split())
            exact_matches = [
                row
                for row in packs
                if str(row.get("pack_id", "")) == wanted
                or str(row.get("title", "")) == wanted
            ]
            packs = exact_matches or [
                row
                for row in packs
                if "".join(str(row.get("pack_id", "")).casefold().split()) == wanted_key
                or _pack_title_reference(row.get("title", ""))
                == _pack_title_reference(wanted)
            ]

        return {
            "mode": "installed_packs",
            "count": len(packs),
            "packs": [_pack_summary(pack_row) for pack_row in packs],
            "presentation_instruction": (
                "Show pack_id, installed_pack_id, and title for every pack in your "
                "answer. The student may use either identifier in later questions."
            ),
            "reference_note": (
                "A pack can be referenced by pack_id, installed_pack_id, displayed "
                "title, or the original filename for a single-file pack. Numeric "
                "installed_pack_id values can have gaps and do not indicate list order. "
                "Text references ignore capitalization and whitespace. Deletion is "
                "the exception: sp2_delete_pack requires installed_pack_id."
            ),
            "question_hint": (
                "The student can ask naturally, for example: 'Use pack Week02 - "
                "Unit Testing and explain dynamic unit testing.' Automatically call "
                "sp2_get_course_context; do not ask for function-call syntax."
            ),
        }

    @mcp.tool()
    def sp2_get_course_context(
        pack: int | str,
        question: str,
    ) -> dict[str, Any]:
        """Answer a normal-language question using one installed course pack.

        Explicit calls with pack and question arguments remain supported. When
        that syntax is omitted, call this tool automatically whenever the user
        names or references an installed pack and asks a factual, explanatory,
        or study question about it. Extract the pack reference and the complete
        question from their prose.

        Examples that should call this tool:
        - "Use pack Week02 - Unit Testing and explain dynamic unit testing."
        - "From week02-unit-testing, what is mutation testing?"
        - "Ask pack 7 to compare static and dynamic unit testing."

        Args:
            pack: Pack name, displayed title, or a single-file pack's original
                filename. The internal installed_pack_id is also accepted.
            question: The user's complete course question in ordinary language.
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
            pack: Pack name, displayed title, or a single-file pack's original
                filename. The internal installed_pack_id is also accepted.
            source_id: Source_id stored for the file inside the pack. Matching
                ignores case and whitespace when it identifies one file
                unambiguously.
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
            pack: Pack name, displayed title, or a single-file pack's original
                filename. The internal installed_pack_id is also accepted.
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
    def sp2_delete_pack(installed_pack_id: int | str) -> dict[str, Any]:
        """Delete one installed SP2 course pack by its exact database id.

        Args:
            installed_pack_id: Positive numeric id shown by sp2_list_packs.
        """
        resolved_installed_pack_id = positive_int(
            installed_pack_id,
            "installed_pack_id",
        )

        deleted_pack = request_backend_json("DELETE", f"/packs/{resolved_installed_pack_id}")
        if not isinstance(deleted_pack, dict):
            raise RuntimeError("SP2 backend API delete-pack response was not an object")

        return {
            "mode": "pack_deleted",
            "resolved_installed_pack_id": resolved_installed_pack_id,
            "deleted_pack": deleted_pack,
        }
