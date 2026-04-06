"""ComicGraph -- LangGraph StateGraph for full comic generation pipeline."""

from langgraph.graph import StateGraph, START, END

from app.graphs.state import WorkflowState
from app.nodes.prompt_node import prompt_node
from app.nodes.condense_node import condense_node
from app.nodes.comic_node import comic_node
from app.nodes.save_node import save_node
from app.prompts.comic_prompt import count_tokens, MAX_PROMPT_TOKENS


def _route_on_token_limit(state: WorkflowState) -> str:
    """Conditional edge: route to condense if over token limit, else comic."""
    if state.get("errors"):
        return END
    token_count = count_tokens(state.get("comic_prompt", ""))
    if token_count > MAX_PROMPT_TOKENS:
        return "condense_node"
    return "comic_node"


def _route_after_condense(state: WorkflowState) -> str:
    """After condense, route to comic_node."""
    if state.get("errors"):
        return END
    return "comic_node"


def build_comic_graph():
    """Build comic generation Graph:
    START -> prompt_node -> [condense_node] -> comic_node -> save_node -> END
    """
    builder = StateGraph(WorkflowState)
    builder.add_node("prompt_node", prompt_node)
    builder.add_node("condense_node", condense_node)
    builder.add_node("comic_node", comic_node)
    builder.add_node("save_node", save_node)

    builder.add_edge(START, "prompt_node")
    builder.add_conditional_edges("prompt_node", _route_on_token_limit)
    builder.add_conditional_edges("condense_node", _route_after_condense)
    builder.add_edge("comic_node", "save_node")
    builder.add_edge("save_node", END)

    return builder.compile()
