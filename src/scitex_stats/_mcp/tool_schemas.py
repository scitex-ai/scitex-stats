"""Default server catalog, collected from authoritative MCP wire metadata.

Discovery starts an in-memory client and invokes no statistical tools. This
catalog describes the package's default server, not a hosted user's session.
"""

from __future__ import annotations

import mcp.types as types
from anyio.from_thread import start_blocking_portal

__all__ = ["get_tool_schemas", "get_tool_schemas_async"]


async def get_tool_schemas_async() -> list[types.Tool]:
    """Read the default server's wire catalog in an existing async context."""
    from fastmcp import Client

    from .._server import mcp

    async with Client(mcp) as client:
        return list(await client.list_tools())


def get_tool_schemas() -> list[types.Tool]:
    """Return wire Tool models, including when called inside an event loop.

    The portal owns a separate loop for this synchronous bridge; it avoids
    nesting asyncio.run in a caller's loop. Async callers can instead await
    get_tool_schemas_async directly. No catalog copy is cached or maintained.
    """
    with start_blocking_portal() as portal:
        return portal.call(get_tool_schemas_async)
