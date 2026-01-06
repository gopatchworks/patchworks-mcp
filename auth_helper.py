from __future__ import annotations
from typing import Optional
from mcp.server.fastmcp import Context


def get_token_from_context(ctx: Optional[Context] = None) -> Optional[str]:
    """
    Extract the Patchworks API token from the request context headers.

    The token is passed automatically from the proxy in the Authorization header
    as "Bearer {token}" and is extracted and used for all Patchworks API calls.

    Args:
        ctx: Optional FastMCP Context object. If None, returns None.

    Returns:
        The full "Bearer {token}" string from the Authorization header, or None if not present.

    Usage in tools:
        @mcp.tool()
        def my_tool(args: MyArgs, ctx: Optional[Context] = None) -> Any:
            token = get_token_from_context(ctx)
            return pw.some_function(..., token=token)
    """
    if ctx is None:
        return None

    try:
        # Access the request context to get headers
        request_ctx = ctx.request_context
        if request_ctx is None or request_ctx.request is None:
            return None

        # Check if the request has headers
        request = request_ctx.request
        if hasattr(request, 'headers'):
            # Look for Authorization header (case-insensitive)
            token = request.headers.get('authorization') or request.headers.get('Authorization')
            return token

        return None
    except Exception:
        return None