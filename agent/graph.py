from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    load_context,
    parse_request,
    respond,
    route_after_parse,
    run_tool,
    save_conversation,
)
from agent.state import AgentState


def build_graph():
    """Construct the StayEase conversation graph."""
    graph = StateGraph(AgentState)

    graph.add_node("load_context", load_context)
    graph.add_node("parse_request", parse_request)
    graph.add_node("run_tool", run_tool)
    graph.add_node("respond", respond)
    graph.add_node("save_conversation", save_conversation)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "parse_request")
    graph.add_conditional_edges(
        "parse_request",
        route_after_parse,
        {
            "run_tool": "run_tool",
            "respond": "respond",
        },
    )
    graph.add_edge("run_tool", "respond")
    graph.add_edge("respond", "save_conversation")
    graph.add_edge("save_conversation", END)
    return graph.compile()
