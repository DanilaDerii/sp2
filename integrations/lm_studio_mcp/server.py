"""LM Studio MCP tools for the SP2 runtime.

This server is intentionally a thin adapter over SP2 backend capabilities.
LM Studio owns the chat UI and final answer generation; SP2 owns pack
operations, retrieval, and structured context return.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp.server.fastmcp import FastMCP

from config.arguments import DEFAULT_MCP_SERVER_NAME
from integrations.lm_studio_mcp.student_tools import register_student_tools
from integrations.lm_studio_mcp.teacher_tools import register_teacher_tools


MCP_SERVER_NAME = DEFAULT_MCP_SERVER_NAME

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


mcp = FastMCP(
    MCP_SERVER_NAME,
    instructions=(
        "Expose SP2 tools to LM Studio. LM Studio writes final answers and summaries. "
        "Use sp2_ingest_source for every local course path; the backend decides "
        "whether to build raw material or install a ZIP pack. When a user says "
        "'use pack X and tell me Y', call sp2_get_course_context with X as pack and "
        "the full question as question. Read tools accept pack names, titles, source "
        "filenames, or installed_pack_id. sp2_delete_pack is different: it requires "
        "the exact numeric installed_pack_id shown by sp2_list_packs."
    ),
)

register_student_tools(mcp)
register_teacher_tools(mcp)


def main() -> None:
    logger.info("Starting SP2 LM Studio MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
