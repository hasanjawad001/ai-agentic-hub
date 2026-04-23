import json
import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from sqlmodel import Session

from backend.models import Agent, Workflow
from backend.services import agent_service


class WorkflowState(TypedDict):
    input: str
    current_node: str
    state_data: Annotated[dict, lambda a, b: {**a, **b}]
    steps: Annotated[list, operator.add]
    iteration: int


def parse_json_from_text(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}") + 1
    if start_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def build_workflow_graph(workflow: Workflow, session: Session):
    graph_data = workflow.graph
    nodes = {n["id"]: n for n in graph_data.get("nodes", [])}
    edges = graph_data.get("edges", [])

    wf = StateGraph(WorkflowState)

    def make_start_node(node_data):
        def start_node(state: WorkflowState) -> dict:
            return {
                "current_node": node_data["id"],
                "state_data": {"input": state["input"]},
                "steps": [{"node_id": node_data["id"], "name": node_data.get("name", "start"), "type": "start", "output": state["input"]}],
                "iteration": 0,
            }
        return start_node

    def make_agent_node(node_data, db_session):
        async def agent_node(state: WorkflowState) -> dict:
            agent_id = node_data.get("agent_id")
            node_name = node_data.get("name", node_data["id"])

            if not agent_id:
                return {
                    "current_node": node_data["id"],
                    "steps": [{"node_id": node_data["id"], "name": node_name, "type": "agent", "output": "Error: no agent assigned", "error": True}],
                    "iteration": state["iteration"] + 1,
                }

            agent = db_session.get(Agent, int(agent_id))
            if not agent:
                return {
                    "current_node": node_data["id"],
                    "steps": [{"node_id": node_data["id"], "name": node_name, "type": "agent", "output": f"Error: agent {agent_id} not found", "error": True}],
                    "iteration": state["iteration"] + 1,
                }

            state_summary = json.dumps(state["state_data"], indent=2)
            task = node_data.get("task", "Process the current state and produce a result.")
            prompt = f"Current workflow state:\n{state_summary}\n\nYour task: {task}"

            result = await agent_service.run_agent(agent, prompt, [], db_session)

            new_state_data = {f"{node_name}_output": result["response"]}
            parsed = parse_json_from_text(result["response"])
            if parsed:
                new_state_data.update(parsed)

            step = {
                "node_id": node_data["id"],
                "name": node_name,
                "type": "agent",
                "output": result["response"],
                "tool_calls": result.get("tool_calls", []),
            }

            return {
                "current_node": node_data["id"],
                "state_data": new_state_data,
                "steps": [step],
                "iteration": state["iteration"] + 1,
            }
        return agent_node

    def make_end_node(node_data):
        def end_node(state: WorkflowState) -> dict:
            return {
                "current_node": node_data["id"],
                "steps": [{"node_id": node_data["id"], "name": node_data.get("name", "end"), "type": "end", "output": json.dumps(state["state_data"], indent=2)}],
            }
        return end_node

    start_node_id = None
    end_node_id = None

    for node_id, node_data in nodes.items():
        node_type = node_data.get("type", "agent")
        if node_type == "start":
            start_node_id = node_id
            wf.add_node(node_id, make_start_node(node_data))
        elif node_type == "end":
            end_node_id = node_id
            wf.add_node(node_id, make_end_node(node_data))
        elif node_type == "agent":
            wf.add_node(node_id, make_agent_node(node_data, session))

    if start_node_id:
        wf.set_entry_point(start_node_id)

    nodes_with_conditions = {}
    for edge in edges:
        src = edge["source"]
        condition = edge.get("condition", "").strip()
        if condition:
            if src not in nodes_with_conditions:
                nodes_with_conditions[src] = []
            nodes_with_conditions[src].append(edge)
        else:
            if src not in nodes_with_conditions:
                nodes_with_conditions[src] = []
            nodes_with_conditions[src].append(edge)

    for src, src_edges in nodes_with_conditions.items():
        has_conditions = any(e.get("condition", "").strip() for e in src_edges)

        if has_conditions:
            def make_router(src_edges, end_id):
                def router(state: WorkflowState) -> str:
                    if state["iteration"] >= 20:
                        return end_id or END

                    data = state["state_data"]
                    for edge in src_edges:
                        condition = edge.get("condition", "").strip()
                        if condition and evaluate_condition(condition, data):
                            return edge["target"]

                    unconditional = [e for e in src_edges if not e.get("condition", "").strip()]
                    if unconditional:
                        return unconditional[0]["target"]

                    return end_id or END
                return router

            targets = {e["target"] for e in src_edges}
            if end_node_id:
                targets.add(end_node_id)
            target_map = {}
            for t in targets:
                if t == end_node_id:
                    target_map[t] = t
                else:
                    target_map[t] = t

            wf.add_conditional_edges(src, make_router(src_edges, end_node_id), target_map)
        else:
            for edge in src_edges:
                tgt = edge["target"]
                if tgt == end_node_id:
                    wf.add_edge(src, tgt)
                else:
                    wf.add_edge(src, tgt)

    if end_node_id:
        wf.add_edge(end_node_id, END)

    return wf.compile()


def evaluate_condition(condition: str, state: dict) -> bool:
    condition = condition.strip()
    if not condition:
        return True

    try:
        for op, func in [
            (" contains ", lambda a, b: b.lower() in str(a).lower()),
            (" != ", lambda a, b: str(a).lower() != b.lower()),
            (" == ", lambda a, b: str(a).lower() == b.lower()),
            (" > ", lambda a, b: float(a) > float(b)),
            (" < ", lambda a, b: float(a) < float(b)),
        ]:
            if op in condition:
                key, value = condition.split(op, 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                actual = state.get(key, "")
                return func(actual, value)
    except Exception:
        pass

    return True


async def run_workflow(workflow: Workflow, initial_input: str, session: Session) -> dict:
    compiled = build_workflow_graph(workflow, session)

    initial_state: WorkflowState = {
        "input": initial_input,
        "current_node": "",
        "state_data": {},
        "steps": [],
        "iteration": 0,
    }

    result = await compiled.ainvoke(initial_state)

    steps = result.get("steps", [])
    state_data = result.get("state_data", {})

    final_output = ""
    for s in reversed(steps):
        if s.get("type") == "agent" and s.get("output"):
            final_output = s["output"]
            break

    return {
        "state": state_data,
        "steps": steps,
        "final_output": final_output,
    }
