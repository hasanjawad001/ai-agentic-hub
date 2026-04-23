import asyncio
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from sqlmodel import Session

from backend.models import Agent, LLMServer, MCPServer
from backend.services import llm_service, mcp_service

AGENT_TIMEOUT = 120


async def resolve_tools(agent: Agent, session: Session):
    lc_tools = []
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
            try:
                tools = await mcp_service.discover_tools(mcp_server)
            except Exception:
                continue
            server_tools_cache[server_id] = (mcp_server, tools)

        mcp_server, tools = server_tools_cache[server_id]

        matching = [t for t in tools if t.get("name") == tool_name]
        if matching:
            try:
                converted = mcp_service.mcp_tools_to_langchain(mcp_server, matching)
                lc_tools.extend(converted)
            except Exception:
                continue

    return lc_tools


async def run_agent(agent: Agent, user_message: str, history: list[dict], session: Session) -> dict:
    llm_server = session.get(LLMServer, agent.llm_server_id)
    if not llm_server:
        return {"response": "Error: LLM server not found.", "history": history, "tool_calls": []}

    try:
        llm = llm_service.get_llm(llm_server)
    except Exception as e:
        return {"response": f"Error connecting to LLM: {e}", "history": history, "tool_calls": []}

    try:
        tools = await resolve_tools(agent, session)
    except Exception as e:
        tools = []

    react_agent = create_react_agent(llm, tools)

    input_messages = [SystemMessage(content=agent.system_prompt)]
    for msg in history:
        if msg["role"] == "user":
            input_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            input_messages.append(AIMessage(content=msg["content"]))
    input_messages.append(HumanMessage(content=user_message))

    try:
        result = await asyncio.wait_for(
            react_agent.ainvoke({"messages": input_messages}),
            timeout=AGENT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return {"response": f"Error: Agent timed out after {AGENT_TIMEOUT}s.", "history": history, "tool_calls": []}
    except Exception as e:
        error_msg = str(e)
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            return {"response": f"Error: Could not connect to LLM server ({llm_server.url}). Is it running?", "history": history, "tool_calls": []}
        return {"response": f"Error: Agent failed — {error_msg[:200]}", "history": history, "tool_calls": []}

    messages = result.get("messages", [])
    final_content = ""
    all_tool_calls = []

    for msg in messages:
        if isinstance(msg, AIMessage):
            if msg.content:
                final_content = msg.content
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    all_tool_calls.append({
                        "tool": tc["name"],
                        "args": tc["args"],
                        "result": "",
                    })
        elif isinstance(msg, ToolMessage):
            if all_tool_calls and not all_tool_calls[-1]["result"]:
                all_tool_calls[-1]["result"] = str(msg.content)[:500]

    if not final_content and not all_tool_calls:
        final_content = "Agent returned no response."

    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_content},
    ]

    return {
        "response": final_content,
        "history": updated_history,
        "tool_calls": all_tool_calls,
    }
