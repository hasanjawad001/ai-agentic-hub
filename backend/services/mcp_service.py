import asyncio
from langchain_core.tools import StructuredTool
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


def _make_mcp_tool_func(server: MCPServer, tool_name: str):
    def tool_func(**kwargs) -> str:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, call_tool(server, tool_name, kwargs)).result()
        return asyncio.run(call_tool(server, tool_name, kwargs))
    return tool_func


def mcp_tools_to_langchain(server: MCPServer, tools: list[dict]) -> list[StructuredTool]:
    lc_tools = []
    for tool in tools:
        if "error" in tool:
            continue

        schema = tool.get("inputSchema", {})
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        args_schema_fields = {}
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "string")
            type_map = {"string": str, "integer": int, "number": float, "boolean": bool}
            args_schema_fields[prop_name] = (
                type_map.get(prop_type, str),
                prop_info.get("description", ""),
            )

        lc_tool = StructuredTool.from_function(
            func=_make_mcp_tool_func(server, tool["name"]),
            name=tool["name"],
            description=tool.get("description", ""),
        )
        lc_tools.append(lc_tool)

    return lc_tools
