import json
from sqlmodel import Session

from backend.models import Agent, Workflow
from backend.services import agent_service


def get_execution_order(graph: dict) -> list[str]:
    """Topological sort of nodes based on edges."""
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    in_degree = {nid: 0 for nid in nodes}
    adjacency = {nid: [] for nid in nodes}

    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if tgt in in_degree:
            in_degree[tgt] += 1
        if src in adjacency:
            adjacency[src].append(edge)

    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order = []

    while queue:
        node_id = queue.pop(0)
        order.append(node_id)
        for edge in adjacency.get(node_id, []):
            tgt = edge["target"]
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)

    return order


def evaluate_condition(condition: str, state: dict) -> bool:
    """Evaluate a simple condition against workflow state.

    Supports: key == value, key != value, key contains value, key > value
    """
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
    """Get next node IDs from current node, evaluating conditions."""
    next_nodes = []
    for edge in edges:
        if edge["source"] != current_id:
            continue
        condition = edge.get("condition", "")
        if not condition or evaluate_condition(condition, state):
            next_nodes.append(edge["target"])
    return next_nodes


async def run_workflow(workflow: Workflow, initial_input: str, session: Session) -> dict:
    """Execute a workflow graph.

    Returns: {state, steps, final_output}
    """
    graph = workflow.graph
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = graph.get("edges", [])

    state = {"input": initial_input}
    steps = []
    visited = set()
    max_steps = 50

    start_nodes = [n["id"] for n in graph["nodes"] if n.get("type") == "start"]
    if not start_nodes:
        order = get_execution_order(graph)
        current_queue = [order[0]] if order else []
    else:
        current_queue = start_nodes

    step_count = 0

    while current_queue and step_count < max_steps:
        node_id = current_queue.pop(0)

        if node_id in visited:
            continue
        visited.add(node_id)
        step_count += 1

        node = nodes.get(node_id)
        if not node:
            continue

        node_type = node.get("type", "agent")
        node_name = node.get("name", node_id)

        step = {"node_id": node_id, "name": node_name, "type": node_type}

        if node_type == "start":
            step["output"] = initial_input
            state["start_output"] = initial_input

        elif node_type == "end":
            step["output"] = json.dumps(state, indent=2)

        elif node_type == "agent":
            agent_id = node.get("agent_id")
            if not agent_id:
                step["output"] = "Error: no agent assigned to this node"
                step["error"] = True
            else:
                agent = session.get(Agent, int(agent_id))
                if not agent:
                    step["output"] = f"Error: agent {agent_id} not found"
                    step["error"] = True
                else:
                    state_summary = json.dumps(state, indent=2)
                    prompt = f"Current workflow state:\n{state_summary}\n\nYour task: {node.get('task', 'Process the current state and produce a result.')}"

                    result = await agent_service.run_agent(agent, prompt, [], session)
                    step["output"] = result["response"]
                    step["tool_calls"] = result.get("tool_calls", [])
                    state[f"{node_name}_output"] = result["response"]

                    try:
                        text = result["response"].strip()
                        if text.startswith("```"):
                            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                        start_idx = text.find("{")
                        end_idx = text.rfind("}") + 1
                        if start_idx != -1 and end_idx > start_idx:
                            text = text[start_idx:end_idx]
                        parsed = json.loads(text)
                        if isinstance(parsed, dict):
                            state.update(parsed)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

        steps.append(step)

        next_nodes = get_next_nodes(node_id, edges, state)
        for nid in next_nodes:
            if nid not in visited:
                current_queue.append(nid)

    final_output = state.get(f"{steps[-1]['name']}_output", "") if steps else ""

    return {
        "state": state,
        "steps": steps,
        "final_output": final_output,
    }
