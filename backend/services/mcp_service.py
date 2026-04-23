import asyncio
from typing import Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model
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
        try:
            if "kwargs" in kwargs and len(kwargs) == 1:
                kwargs = kwargs["kwargs"]
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(call_tool(server, tool_name, kwargs))
            finally:
                loop.close()
        except Exception as e:
            return f"Error calling tool {tool_name}: {e}"
    return tool_func


def _build_args_schema(tool_name: str, schema: dict) -> type[BaseModel]:
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    type_map = {"string": str, "integer": int, "number": float, "boolean": bool}

    fields = {}
    for prop_name, prop_info in properties.items():
        py_type = type_map.get(prop_info.get("type", "string"), str)
        description = prop_info.get("description", "")
        if prop_name in required:
            fields[prop_name] = (py_type, Field(description=description))
        else:
            fields[prop_name] = (Optional[py_type], Field(default=None, description=description))

    return create_model(f"{tool_name}_args", **fields)


def mcp_tools_to_langchain(server: MCPServer, tools: list[dict]) -> list[StructuredTool]:
    lc_tools = []
    for tool in tools:
        if "error" in tool:
            continue

        schema = tool.get("inputSchema", {})
        args_schema = _build_args_schema(tool["name"], schema)

        lc_tool = StructuredTool.from_function(
            func=_make_mcp_tool_func(server, tool["name"]),
            name=tool["name"],
            description=tool.get("description", ""),
            args_schema=args_schema,
        )
        lc_tools.append(lc_tool)

    return lc_tools
