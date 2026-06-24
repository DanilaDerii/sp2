"""LM Studio MCP server for SP2 course context retrieval.

Run with: python server.py
LM Studio connects to this via stdio using mcp.json.
"""

from __future__ import annotations

import requests
from mcp.server.fastmcp import FastMCP

SP2_API_BASE = "http://127.0.0.1:8001"

mcp = FastMCP("SP2 Course Assistant")


@mcp.tool()
def sp2_list_packs() -> str:
    """List all installed SP2 course packs available for retrieval."""
    response = requests.get(f"{SP2_API_BASE}/packs", timeout=10)
    response.raise_for_status()
    packs = response.json()
    if not packs:
        return "No course packs are currently installed."
    lines = []
    for pack in packs:
        active = "active" if pack["is_active"] else "inactive"
        lines.append(
            f"id={pack['id']} | {pack['title']}"
            f" (pack_id={pack['pack_id']}, version={pack['version']}, {active})"
        )
    return "\n".join(lines)


@mcp.tool()
def sp2_get_course_context(
    installed_pack_id: int,
    question: str,
    top_k: int | None = None,
) -> str:
    """Retrieve course context from an installed SP2 pack for a student question.

    Returns relevant course chunk text and source metadata if found, or a
    no-context message if the topic is not covered by the installed pack.
    Use installed_pack_id from sp2_list_packs.
    """
    payload: dict = {"installed_pack_id": installed_pack_id, "question": question}
    if top_k is not None:
        payload["top_k"] = top_k

    response = requests.post(
        f"{SP2_API_BASE}/retrieval/context",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    packet = response.json()

    if packet["mode"] == "no_course_context":
        return packet["message"]

    lines = [
        f"Course context for: {packet['question']}",
        f"Pack: {packet['pack_id']}",
        "",
    ]
    for i, chunk in enumerate(packet["chunks"], 1):
        source_ref = chunk["source_title"]
        if chunk.get("page"):
            source_ref += f" p.{chunk['page']}"
        if chunk.get("section"):
            source_ref += f" — {chunk['section']}"
        lines.append(f"[{i}] {source_ref}")
        lines.append(chunk["text"])
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def sp2_import_pack_from_path(pack_zip_path: str) -> str:
    """Import a teacher-exported SP2 course pack zip into the local student runtime.

    Provide the full filesystem path to the .zip file.
    """
    response = requests.post(
        f"{SP2_API_BASE}/packs/import-path",
        json={"pack_zip_path": pack_zip_path},
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    pack = result["installed_pack"]
    return (
        f"Pack imported successfully.\n"
        f"Title: {pack['title']}\n"
        f"Pack ID: {pack['pack_id']}\n"
        f"Version: {pack['version']}\n"
        f"Installed ID: {pack['id']}\n"
        f"Chunks: {result['chunk_count']}\n"
        f"Path: {result['install_path']}"
    )


if __name__ == "__main__":
    mcp.run()
