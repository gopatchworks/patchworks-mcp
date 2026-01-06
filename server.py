from __future__ import annotations
import sys, logging, base64
from typing import Any

from mcp.server.fastmcp import FastMCP
from defaults.tools import register_default_tools
from custom.tools import register_custom_tools

# Log to STDERR only (stdio transport cannot receive stdout noise)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger("patchworks-mcp")

mcp = FastMCP("patchworks")

# Register default Patchworks tools
register_default_tools(mcp)

# Register user-defined custom tools
register_custom_tools(mcp)


@mcp.tool()
def list_tools() -> Any:
    """
    List all available tools in this MCP server with their descriptions and parameters.
    Useful for discovering what operations are available.
    """
    # Combine default and custom tool registries
    tools_list = []

    # Add default tools
    if hasattr(mcp, '_default_tools_registry'):
        tools_list.extend(mcp._default_tools_registry)

    # Add custom tools
    if hasattr(mcp, '_custom_tools_registry'):
        tools_list.extend(mcp._custom_tools_registry)

    return {
        "tools": tools_list,
        "count": len(tools_list),
        "server": "patchworks",
        "note": "For detailed parameter schemas, use the MCP protocol's built-in 'tools/list' method"
    }


if __name__ == "__main__":
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = 8020
    mcp.run(transport='streamable-http')