from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from backend.database import get_session
from backend.models import Workflow
from backend.services import workflow_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("/")
def list_workflows(session: Session = Depends(get_session)):
    return session.exec(select(Workflow)).all()


@router.post("/")
def create_workflow(workflow: Workflow, session: Session = Depends(get_session)):
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    return workflow


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, session: Session = Depends(get_session)):
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        return {"error": "not found"}
    return workflow


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: int, request: Request, session: Session = Depends(get_session)):
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        return {"error": "not found"}
    body = await request.json()
    if "name" in body:
        workflow.name = body["name"]
    if "graph" in body:
        workflow.graph = body["graph"]
    session.add(workflow)
    session.commit()
    session.refresh(workflow)
    return workflow


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int, session: Session = Depends(get_session)):
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        return {"error": "not found"}
    session.delete(workflow)
    session.commit()
    return {"ok": True}


@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: int, request: Request, session: Session = Depends(get_session)):
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        return {"error": "not found"}

    body = await request.json()
    initial_input = body.get("input", "")

    result = await workflow_service.run_workflow(workflow, initial_input, session)
    return result
