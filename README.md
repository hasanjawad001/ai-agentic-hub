# AI Agentic Hub

A web GUI to visually build AI agents and workflows using local or cloud LLMs and MCP tool servers. No code required — create agents, connect tools, and build complex agentic workflows from a visual editor.

## Features

- **Multi-Provider LLM Support** — connect to Ollama (local), OpenAI, or Anthropic from the same GUI
- **MCP Tool Server Management** — add MCP servers, auto-discover tools via MCP SDK
- **Agent Builder** — create/edit/delete agents with custom system prompts, select any LLM and MCP tools
- **Agent Chat** — chat with agents, see tool calls and results in real time
- **Visual Workflow Editor** — drag-and-drop DAG editor (Drawflow) to build agentic workflows
- **Orchestrator Loop Pattern** — an orchestrator agent dynamically routes tasks to specialist agents and loops until done
- **Conditional Edges** — route workflow paths based on state (e.g. `needs_math == true`)
- **Shared Workflow State** — typed state (LangGraph StateGraph) passes between nodes
- **ReAct Agents** — agents use LangChain/LangGraph ReAct pattern (reason, act, observe, repeat)
- **Mix Providers** — use different LLMs for different agents in the same workflow (e.g. orchestrator on Claude, workers on local Ollama)

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [Ollama](https://ollama.com/) installed and running with a model (e.g. `ollama pull qwen3.5:9b`)
- (Optional) OpenAI or Anthropic API key for cloud LLMs
- (Optional) An MCP tool server to connect

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/hasanjawad001/ai-agentic-hub.git
cd ai-agentic-hub
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

### 2. Start the example MCP tool server (optional)

In a separate terminal:

```bash
source .venv/bin/activate
start-mcp
```

This starts 8 example tools on port 3000: `add`, `subtract`, `multiply`, `divide`, `reverse_string`, `uppercase`, `lowercase`, `int_to_string`.

### 3. Start the hub

```bash
source .venv/bin/activate
start-hub
```

Open http://localhost:8000

### 4. Set up in the GUI

1. **LLM Servers** — Add your LLM server:
   - Ollama: provider=`ollama`, url=`http://localhost:11434`, model=`qwen3.5:9b`
   - OpenAI: provider=`openai`, model=`gpt-4o`, api_key=`sk-...`
   - Anthropic: provider=`anthropic`, model=`claude-sonnet-4-20250514`, api_key=`sk-ant-...`
2. **MCP Servers** — Add your MCP server (url: `http://localhost:3000`) and click Discover Tools
3. **Agents** — Create agents with system prompts and selected tools
4. **Workflows** — Create a workflow, open the editor, drag nodes, connect them, and run

## Example: Orchestrator Workflow

Build a workflow where an orchestrator agent dynamically routes tasks to specialists:

```
Start -> Orchestrator <-> Math Agent (loop back)
                      <-> Text Agent (loop back)
         Orchestrator -> End (when done)
```

**Input:** `compute ((5+5)/(4-2))*3, convert to string, uppercase it, then reverse it`

**Result:** The orchestrator loops 3 times — sends math to the math agent (add, subtract, divide, multiply = 15), then sends text processing to the text agent (uppercase, reverse = "0.51"), then signals done.

All from the visual editor. No code written.

## Project Structure

```
ai-agentic-hub/
├── backend/
│   ├── main.py                 # FastAPI app + page routes
│   ├── database.py             # SQLite setup
│   ├── models.py               # LLMServer, MCPServer, Agent, Workflow
│   ├── api/
│   │   ├── llm_routes.py       # LLM server CRUD + health check
│   │   ├── mcp_routes.py       # MCP server CRUD + tool discovery
│   │   ├── agent_routes.py     # Agent CRUD + chat
│   │   └── workflow_routes.py  # Workflow CRUD + run
│   └── services/
│       ├── llm_service.py      # LangChain LLM client (Ollama/OpenAI/Anthropic)
│       ├── mcp_service.py      # MCP SDK client + LangChain tool conversion
│       ├── agent_service.py    # LangGraph ReAct agent
│       └── workflow_service.py # LangGraph StateGraph workflow engine
├── frontend/templates/         # Jinja2 HTML templates (dark theme)
├── examples/
│   └── test_mcp_server.py      # Example MCP server with 8 tools
├── pyproject.toml
└── LICENSE
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLModel, SQLite
- **Frontend:** Jinja2 templates, vanilla JavaScript
- **Agent Engine:** [LangChain](https://python.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) (ReAct agents, StateGraph workflows)
- **LLM Providers:** [langchain-ollama](https://pypi.org/project/langchain-ollama/), [langchain-openai](https://pypi.org/project/langchain-openai/), [langchain-anthropic](https://pypi.org/project/langchain-anthropic/)
- **Workflow Editor:** [Drawflow](https://github.com/jerosoler/Drawflow)
- **MCP Client:** [mcp](https://pypi.org/project/mcp/) Python SDK
- **MCP Server (example):** [FastMCP](https://pypi.org/project/fastmcp/)

## License

MIT
