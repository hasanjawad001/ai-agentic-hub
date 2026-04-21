import json
from sqlmodel import Session

from backend.models import Agent, LLMServer, MCPServer
from backend.services import llm_service, mcp_service

MAX_TURNS = 15


async def resolve_tools(agent: Agent, session: Session) -> tuple[list[dict], dict]:
    """Resolve agent's tool_ids into schemas and a mapping of tool_name -> mcp_server.

    tool_ids format: ["mcp:SERVER_ID:TOOL_NAME", ...]
    Returns: (tool_schemas, tool_map) where tool_map = {tool_name: MCPServer}
    """
    tool_schemas = []
    tool_map = {}

    server_tools_cache = {}

    for tool_id in agent.tool_ids:
        if not tool_id.startswith("mcp:"):
            continue

        parts = tool_id.split(":", 2)
        if len(parts) != 3:
            continue

        _, server_id, tool_name = parts
        server_id = int(server_id)

        if server_id not in server_tools_cache:
            mcp_server = session.get(MCPServer, server_id)
            if not mcp_server:
                continue
            tools = await mcp_service.discover_tools(mcp_server)
            server_tools_cache[server_id] = (mcp_server, tools)

        mcp_server, tools = server_tools_cache[server_id]

        for tool in tools:
            if tool.get("name") == tool_name:
                tool_map[tool_name] = mcp_server
                tool_schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
                    },
                })

    return tool_schemas, tool_map


async def run_agent(agent: Agent, user_message: str, history: list[dict], session: Session) -> dict:
    """Run the agentic loop for a single agent."""
    llm_server = session.get(LLMServer, agent.llm_server_id)
    if not llm_server:
        return {"response": "Error: LLM server not found.", "history": history, "tool_calls": []}

    tool_schemas, tool_map = await resolve_tools(agent, session)

    messages = [{"role": "system", "content": agent.system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    all_tool_calls = []

    for turn in range(MAX_TURNS):
        response = llm_service.chat(llm_server, messages, tools=tool_schemas if tool_schemas else None)
        messages.append(response)

        if not response.get("tool_calls"):
            break

        for tc in response["tool_calls"]:
            func = tc["function"]
            name = func["name"]
            args = func["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            mcp_server = tool_map.get(name)
            if mcp_server:
                result = await mcp_service.call_tool(mcp_server, name, args)
            else:
                result = f"Error: tool '{name}' not found"

            all_tool_calls.append({"tool": name, "args": args, "result": result[:500]})
            messages.append({"role": "tool", "content": result})

    final_content = response.get("content", "") if response else ""

    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_content},
    ]

    return {
        "response": final_content,
        "history": updated_history,
        "tool_calls": all_tool_calls,
    }
