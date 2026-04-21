from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

from backend.models import MCPServer


async def discover_tools(server: MCPServer) -> list[dict]:
    try:
        url = server.url.rstrip("/") + "/mcp"
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "inputSchema": t.inputSchema if hasattr(t, "inputSchema") else {},
                    }
                    for t in result.tools
                ]
    except Exception as e:
        return [{"error": str(e)}]


async def call_tool(server: MCPServer, tool_name: str, arguments: dict) -> str:
    try:
        url = server.url.rstrip("/") + "/mcp"
        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                parts = []
                for content in result.content:
                    if hasattr(content, "text"):
                        parts.append(content.text)
                    else:
                        parts.append(str(content))
                return "\n".join(parts) if parts else str(result)
    except Exception as e:
        return f"Error calling tool: {e}"


def tools_to_schemas(tools: list[dict]) -> list[dict]:
    schemas = []
    for tool in tools:
        if "error" in tool:
            continue
        schemas.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
            },
        })
    return schemas
