"""
MCP client — this is what makes the Orchestrator an MCP *client* rather than
just another service calling the Application API directly. It asks the MCP
server for exactly the tools/data it needs (get_project_state,
list_project_documents) instead of trusting whatever context a caller hands
it, per the design doc's MCP-based architecture.

Note on the mcp SDK: the ClientSession / streamablehttp_client API shown here
matches recent versions of the `mcp` Python package. If your installed
version's import paths differ, check `python -c "import mcp; print(mcp.__file__)"`
and the package's own examples — this has moved around across releases.
"""
import os
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")


def _extract_tool_json(tool_result):
    for block in tool_result.content:
        if getattr(block, "type", None) == "text":
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                return block.text
    return None


async def fetch_project_context(project_id: str) -> dict:
    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            state_result = await session.call_tool("get_project_state", {"project_id": project_id})
            docs_result = await session.call_tool("list_project_documents", {"project_id": project_id})
            return {
                "state": _extract_tool_json(state_result) or {},
                "documents": _extract_tool_json(docs_result) or [],
            }
