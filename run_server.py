"""Entry point for Finance MCP Server (stdio transport)."""

from server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
