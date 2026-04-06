"""Prompt building node — construct visual comic prompt from script data."""

import logging

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.prompts.comic_prompt import build_comic_prompt

logger = logging.getLogger(__name__)


async def prompt_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Build comic visual prompt from script data.

    Returns: {"comic_prompt": str}
    """
    comic_prompt = build_comic_prompt(
        slang=state["slang"],
        origin=state["origin"],
        explanation=state["explanation"],
        panels=state["panels"],
    )
    logger.info(
        "Comic prompt built: %d characters", len(comic_prompt),
    )
    return {"comic_prompt": comic_prompt}
