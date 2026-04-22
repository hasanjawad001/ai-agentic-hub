import json
from sqlmodel import Session

from backend.models import Agent, Workflow
from backend.services import agent_service


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


def get_next_nodes(current_id: str, edges: list[dict], state: dict) -> list[str]:
    next_nodes = []
    for edge in edges:
        if edge["source"] != current_id:
            continue
        condition = edge.get("condition", "")
        if not condition or evaluate_condition(condition, state):
            next_nodes.append(edge["target"])
    return next_nodes


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


async def run_node(node: dict, state: dict, session: Session) -> dict:
    node_type = node.get("type", "agent")
    node_name = node.get("name", node["id"])

    step = {"node_id": node["id"], "name": node_name, "type": node_type}

    if node_type == "start":
        step["output"] = state.get("input", "")

    elif node_type == "end":
        step["output"] = json.dumps(state, indent=2)

    elif node_type == "agent":
        agent_id = node.get("agent_id")
        if not agent_id:
            step["output"] = "Error: no agent assigned"
            step["error"] = True
            return step

        agent = session.get(Agent, int(agent_id))
        if not agent:
            step["output"] = f"Error: agent {agent_id} not found"
            step["error"] = True
            return step

        state_summary = json.dumps(state, indent=2)
        task = node.get("task", "Process the current state and produce a result.")
        prompt = f"Current workflow state:\n{state_summary}\n\nYour task: {task}"

        result = await agent_service.run_agent(agent, prompt, [], session)
        step["output"] = result["response"]
        step["tool_calls"] = result.get("tool_calls", [])

        state[f"{node_name}_output"] = result["response"]

        parsed = parse_json_from_text(result["response"])
        if parsed:
            state.update(parsed)

    return step


async def run_workflow(workflow: Workflow, initial_input: str, session: Session) -> dict:
    graph = workflow.graph
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    state = {"input": initial_input}
    steps = []
    max_iterations = 20

    start_nodes = [n["id"] for n in graph["nodes"] if n.get("type") == "start"]
    current_queue = start_nodes if start_nodes else [graph["nodes"][0]["id"]]

    iteration = 0

    while current_queue and iteration < max_iterations:
        node_id = current_queue.pop(0)
        iteration += 1

        node = nodes.get(node_id)
        if not node:
            continue

        step = await run_node(node, state, session)
        steps.append(step)

        if node.get("type") == "end":
            break

        if step.get("error"):
            continue

        next_nodes = get_next_nodes(node_id, edges, state)
        for nid in next_nodes:
            current_queue.append(nid)

    final_output = ""
    for s in reversed(steps):
        if s.get("type") == "agent" and s.get("output"):
            final_output = s["output"]
            break

    return {
        "state": state,
        "steps": steps,
        "final_output": final_output,
    }
