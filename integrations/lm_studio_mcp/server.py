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

from integrations.lm_studio_mcp.student_tools import register_student_tools
from integrations.lm_studio_mcp.teacher_tools import register_teacher_tools


MCP_SERVER_NAME = "sp2-course-context"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


mcp = FastMCP(
    MCP_SERVER_NAME,
    instructions=(
        "Expose SP2 tools to LM Studio. Tools can build teacher packs, import "
        "packs, return installed pack metadata, and return retrieval context. "
        "LM Studio writes final answers."
    ),
)

register_student_tools(mcp)
register_teacher_tools(mcp)


def main() -> None:
    logger.info("Starting SP2 LM Studio MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
