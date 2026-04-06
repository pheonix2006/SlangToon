"""ScriptGraph -- LangGraph StateGraph for script generation."""

from langgraph.graph import StateGraph, START, END

from app.graphs.state import WorkflowState
from app.nodes.script_node import script_node


def build_script_graph():
    """Build script generation Graph: START -> script_node -> END."""
    builder = StateGraph(WorkflowState)
    builder.add_node("script_node", script_node)
    builder.add_edge(START, "script_node")
    builder.add_edge("script_node", END)
    return builder.compile()
