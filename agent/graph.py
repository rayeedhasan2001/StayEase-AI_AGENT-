from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes import book_node, details_node, search_node
from agent.state import AgentState


def route_to_executor(state: AgentState) -> str:
    """Choose the executor node from the orchestrator result."""
    target = state["executor_target"]
    if target not in {"search_node", "details_node", "book_node"}:
        raise ValueError(f"Unsupported executor target: {target}")
    return target


def build_graph():
    """Construct the lightweight executor graph."""
    graph = StateGraph(AgentState)

    graph.add_node("search_node", search_node)
    graph.add_node("details_node", details_node)
    graph.add_node("book_node", book_node)

    graph.add_conditional_edges(
        START,
        route_to_executor,
        {
            "search_node": "search_node",
            "details_node": "details_node",
            "book_node": "book_node",
        },
    )
    graph.add_edge("search_node", END)
    graph.add_edge("details_node", END)
    graph.add_edge("book_node", END)
    return graph.compile()
