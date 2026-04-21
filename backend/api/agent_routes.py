from fastapi import APIRouter, Depends, Request
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

    result = await agent_service.run_agent(agent, message, history, session)

    chat_histories[agent_id] = result["history"]

    return {
        "response": result["response"],
        "tool_calls": result["tool_calls"],
    }


@router.post("/{agent_id}/clear")
def clear_history(agent_id: int):
    chat_histories.pop(agent_id, None)
    return {"ok": True}
