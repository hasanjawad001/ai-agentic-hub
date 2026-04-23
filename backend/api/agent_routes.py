from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Agent
from backend.services import agent_service

router = APIRouter(prefix="/api/agents", tags=["agents"])

chat_histories: dict[int, list[dict]] = {}


@router.get("/")
def list_agents(session: Session = Depends(get_session)):
    return session.exec(select(Agent)).all()


@router.post("/")
def create_agent(agent: Agent, session: Session = Depends(get_session)):
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.get("/{agent_id}")
def get_agent(agent_id: int, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        return {"error": "not found"}
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: int, request: Request, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        return {"error": "not found"}
    body = await request.json()
    if "name" in body:
        agent.name = body["name"]
    if "system_prompt" in body:
        agent.system_prompt = body["system_prompt"]
    if "llm_server_id" in body:
        agent.llm_server_id = body["llm_server_id"]
    if "tool_ids" in body:
        agent.tool_ids = body["tool_ids"]
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        return {"error": "not found"}
    chat_histories.pop(agent_id, None)
    session.delete(agent)
    session.commit()
    return {"ok": True}


@router.post("/{agent_id}/chat")
async def chat(agent_id: int, request: Request, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        return {"error": "not found"}

    body = await request.json()
    message = body.get("message", "")
    history = chat_histories.get(agent_id, [])

    try:
        result = await agent_service.run_agent(agent, message, history, session)
    except Exception as e:
        return {
            "response": f"Error: {str(e)[:200]}",
            "tool_calls": [],
        }

    chat_histories[agent_id] = result["history"]

    return {
        "response": result["response"],
        "tool_calls": result["tool_calls"],
    }


@router.post("/{agent_id}/chat/stream")
async def chat_stream(agent_id: int, request: Request, session: Session = Depends(get_session)):
    agent = session.get(Agent, agent_id)
    if not agent:
        return {"error": "not found"}

    body = await request.json()
    message = body.get("message", "")
    history = chat_histories.get(agent_id, [])

    async def event_generator():
        full_content = ""
        async for event in agent_service.stream_agent(agent, message, history, session):
            yield event
            import json
            try:
                data = json.loads(event.replace("data: ", "").strip())
                if data.get("type") == "done":
                    full_content = data.get("content", "")
            except Exception:
                pass

        chat_histories[agent_id] = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": full_content},
        ]

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{agent_id}/clear")
def clear_history(agent_id: int):
    chat_histories.pop(agent_id, None)
    return {"ok": True}
