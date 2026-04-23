from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import MCPServer
from backend.services import mcp_service

router = APIRouter(prefix="/api/mcp-servers", tags=["mcp-servers"])


@router.get("/")
def list_servers(session: Session = Depends(get_session)):
    return session.exec(select(MCPServer)).all()


@router.post("/")
def create_server(server: MCPServer, session: Session = Depends(get_session)):
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


@router.put("/{server_id}")
async def update_server(server_id: int, request: Request, session: Session = Depends(get_session)):
    server = session.get(MCPServer, server_id)
    if not server:
        return {"error": "not found"}
    body = await request.json()
    for field in ("name", "url"):
        if field in body:
            setattr(server, field, body[field])
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


@router.delete("/{server_id}")
def delete_server(server_id: int, session: Session = Depends(get_session)):
    server = session.get(MCPServer, server_id)
    if not server:
        return {"error": "not found"}
    session.delete(server)
    session.commit()
    return {"ok": True}


@router.get("/{server_id}/tools")
async def discover_tools(server_id: int, session: Session = Depends(get_session)):
    server = session.get(MCPServer, server_id)
    if not server:
        return {"error": "not found"}
    return await mcp_service.discover_tools(server)
