"""
Custom tools for your MCP server.

Guidelines:
1. All tools must be defined INSIDE the register_custom_tools() function
2. Use the @mcp.tool() decorator for each tool
3. Define argument schemas in custom/schemas.py
4. Import any additional libraries you need at the top
5. Helper functions should also be defined inside register_custom_tools()

Example structure:
    @mcp.tool()
    def my_tool(args: MyToolArgs) -> Any:
        '''Tool description that appears in MCP.'''
        # Your implementation here
        return {"result": "success"}
"""

from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


# from custom.schemas import ExampleToolArgs


# Import any additional libraries you need
# import requests
# import json

class ExampleToolArgs(BaseModel):
    """Example arguments schema for a custom tool."""
    name: str = Field(..., description="The name parameter")
    count: int = Field(1, ge=1, le=100, description="Count between 1 and 100")
    optional_param: Optional[str] = Field(None, description="An optional parameter")



def register_custom_tools(mcp: FastMCP):
    """
    Register all custom tools here.

    IMPORTANT: All @mcp.tool() decorated functions must be defined INSIDE this function
    so that they have access to the mcp instance.
    """

    # Track custom tools for list_tools() function
    if not hasattr(mcp, '_custom_tools_registry'):
        mcp._custom_tools_registry = []

    # ------------------------------------------------------------------------------
    # Example Tool (remove or replace with your own)
    # ------------------------------------------------------------------------------

    @mcp.tool()
    def example_tool(args: ExampleToolArgs) -> Any:
        """
        An example custom tool that demonstrates the structure.

        This tool takes a name and count, and returns a greeting message repeated.
        Replace this with your own tool implementation.
        """
        greeting = f"Hello, {args.name}!"

        if args.optional_param:
            greeting += f" ({args.optional_param})"

        return {
            "message": greeting,
            "repeated": [greeting] * args.count,
            "total_count": args.count
        }

    # Register this tool in the registry
    mcp._custom_tools_registry.append({
        "name": "example_tool",
        "description": "An example custom tool that demonstrates the structure. This tool takes a name and count, and returns a greeting message repeated. Replace this with your own tool implementation.",
        "category": "custom"
    })

    # ------------------------------------------------------------------------------
    # Add Your Custom Tools Below
    # ------------------------------------------------------------------------------

    # Example pattern for a new tool:
    #
    # @mcp.tool()
    # def my_custom_tool(args: MyCustomToolArgs) -> Any:
    #     """
    #     Description of what your tool does.
    #     This appears in the MCP tools/list response.
    #     """
    #     # Your implementation here
    #     result = do_something(args.param1, args.param2)
    #     return result
    #
    # # Don't forget to register it!
    # mcp._custom_tools_registry.append({
    #     "name": "my_custom_tool",
    #     "description": "Description of what your tool does.",
    #     "category": "custom"  # or use a more specific category like "data", "api", etc.
    # })

    # Helper functions (if needed) should also be inside this function:
    #
    # def my_helper_function(data: str) -> str:
    #     """Helper function for tool processing."""
    #     return data.upper()
    #
    # @mcp.tool()
    # def tool_using_helper(args: SomeArgs) -> Any:
    #     """Tool that uses the helper function."""
    #     processed = my_helper_function(args.data)
    #     return {"result": processed}
    #
    # mcp._custom_tools_registry.append({
    #     "name": "tool_using_helper",
    #     "description": "Tool that uses the helper function.",
    #     "category": "custom"
    # })