import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.database import init_db
from backend.api import llm_routes, mcp_routes, agent_routes, workflow_routes

app = FastAPI(title="AI Agentic Hub", version="0.1.0")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend", "static")), name="static")

app.include_router(llm_routes.router)
app.include_router(mcp_routes.router)
app.include_router(agent_routes.router)
app.include_router(workflow_routes.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")


@app.get("/llm-servers")
def llm_servers_page(request: Request):
    return templates.TemplateResponse(request, "llm_servers.html")


@app.get("/mcp-servers")
def mcp_servers_page(request: Request):
    return templates.TemplateResponse(request, "mcp_servers.html")


@app.get("/agents")
def agents_page(request: Request):
    return templates.TemplateResponse(request, "agents.html")


@app.get("/agents/{agent_id}/chat")
def agent_chat_page(request: Request, agent_id: int):
    return templates.TemplateResponse(request, "chat.html", {"agent_id": agent_id})


@app.get("/workflows")
def workflows_page(request: Request):
    return templates.TemplateResponse(request, "workflows.html")


@app.get("/workflows/{workflow_id}/editor")
def workflow_editor_page(request: Request, workflow_id: int):
    return templates.TemplateResponse(request, "workflow_editor.html", {"workflow_id": workflow_id})


def run():
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    run()
