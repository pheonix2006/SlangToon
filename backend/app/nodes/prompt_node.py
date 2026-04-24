"""Prompt building node — construct visual comic prompt from script data."""

import logging

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.prompts.comic_prompt import build_comic_prompt
from app.prompts.theme_packs import get_theme_by_id

logger = logging.getLogger(__name__)


async def prompt_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Build comic visual prompt from script data.

    Returns: {"comic_prompt": str}
    """
    visual_style = ""
    theme_id = state.get("theme_id")
    if theme_id:
        theme = get_theme_by_id(theme_id)
        if theme:
            visual_style = theme["visual_style"]

    comic_prompt = build_comic_prompt(
        slang=state["slang"],
        origin=state["origin"],
        explanation=state["explanation"],
        panels=state["panels"],
        has_reference_image=bool(state.get("reference_image")),
        visual_style=visual_style,
    )
    logger.info(
        "Comic prompt built: %d characters", len(comic_prompt),
    )
    return {"comic_prompt": comic_prompt}
