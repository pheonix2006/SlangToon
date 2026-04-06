"""Condense node — LLM-based prompt compression when over token limit."""

import logging

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.prompts.comic_prompt import (
    build_comic_prompt,
    _truncate_prompt_to_tokens,
    MAX_PROMPT_TOKENS,
)
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


async def condense_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Try LLM condense, fall back to hard truncation on failure.

    Returns: {"comic_prompt": str}
    """
    settings = config["configurable"]["settings"]
    current_prompt = state["comic_prompt"]

    # Try LLM condense
    llm = LLMClient(settings)
    try:
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT

        content = await llm.chat(
            system_prompt=CONDENSE_SYSTEM_PROMPT,
            user_text=current_prompt,
            temperature=0.3,
        )
        condensed = LLMClient.extract_json_from_content(content)
        if condensed and "panels" in condensed:
            new_prompt = build_comic_prompt(
                slang=condensed.get("slang", ""),
                origin=condensed.get("origin", ""),
                explanation=condensed.get("explanation", ""),
                panels=condensed["panels"],
            )
            logger.info("LLM condense succeeded: prompt %d -> %d chars", len(current_prompt), len(new_prompt))
            return {"comic_prompt": new_prompt}
        logger.warning("LLM condense returned invalid structure, falling back to truncation")
    except Exception as exc:
        logger.warning("LLM condense failed, falling back to truncation: %s", exc)

    # Final fallback: hard truncation
    truncated = _truncate_prompt_to_tokens(current_prompt, MAX_PROMPT_TOKENS)
    logger.warning("Prompt hard-truncated to %d tokens", MAX_PROMPT_TOKENS)
    return {"comic_prompt": truncated}
