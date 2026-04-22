# AI Agentic Hub

A web GUI to visually build AI agents and workflows using local LLMs (via Ollama) and MCP tool servers. No code required — create agents, connect tools, and build complex agentic workflows from a visual editor.

## Features

- **LLM Server Management** — connect to Ollama, OpenAI, or Anthropic with health checks
- **MCP Tool Server Management** — add MCP servers, auto-discover tools
- **Agent Builder** — create agents with custom system prompts, select LLM and MCP tools
- **Agent Chat** — chat with agents, see tool calls and results in real time
- **Visual Workflow Editor** — drag-and-drop DAG editor (Drawflow) to build agentic workflows
- **Orchestrator Loop Pattern** — an orchestrator agent dynamically routes tasks to specialist agents and loops until done
- **Conditional Edges** — route workflow paths based on state (e.g. `needs_math == true`)
- **Shared Workflow State** — JSON state passes between nodes, each agent reads and writes to it

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.com/) installed and running with a model (e.g. `ollama pull qwen3.5:9b`)
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
cd ai-agentic-hub
source .venv/bin/activate
python examples/test_mcp_server.py
```

This starts 8 example tools on port 3000: `add`, `subtract`, `multiply`, `divide`, `reverse_string`, `uppercase`, `lowercase`, `int_to_string`.

### 3. Start the hub

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

Open http://localhost:8000

### 4. Set up in the GUI

1. **LLM Servers** — Add your Ollama server (url: `http://localhost:11434`, model: `qwen3.5:9b`)
2. **MCP Servers** — Add your MCP server (url: `http://localhost:3000`) and click Discover Tools
3. **Agents** — Create agents with system prompts and selected tools
4. **Workflows** — Create a workflow, open the editor, drag nodes, connect them, and run

## Example: Orchestrator Workflow

Build a workflow where an orchestrator agent dynamically routes tasks to specialists:

```
Start → Orchestrator ⟷ Math Agent (loop back)
                     ⟷ Text Agent (loop back)
        Orchestrator → End (when done)
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
│       ├── llm_service.py      # Ollama/OpenAI client
│       ├── mcp_service.py      # MCP SDK client
│       ├── agent_service.py    # Agentic loop
│       └── workflow_service.py # DAG execution engine
├── frontend/templates/         # Jinja2 HTML templates
├── examples/
│   └── test_mcp_server.py      # Example MCP server with 8 tools
├── pyproject.toml
└── LICENSE
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLModel, SQLite
- **Frontend:** Jinja2 templates, vanilla JavaScript
- **Workflow Editor:** [Drawflow](https://github.com/jerosoler/Drawflow)
- **MCP Client:** [mcp](https://pypi.org/project/mcp/) Python SDK
- **LLM Client:** [ollama](https://pypi.org/project/ollama/) + [openai](https://pypi.org/project/openai/) SDKs

## License

MIT
