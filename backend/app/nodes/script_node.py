"""Script generation node — LLM call for slang + comic script."""

import logging

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_USER_TEXT = (
    "Pick a classical idiom, proverb, or traditional saying from any culture "
    "— something with historical depth and cultural resonance. "
    "Reimagine it as a modern comic. Respond with JSON only."
)


async def script_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Call GLM-4.6V to generate random slang + 8-12 panel comic script.

    Returns: Partial WorkflowState update dict.
    Raises: LLMTimeoutError, LLMApiError, LLMResponseError, ValueError.
    """
    settings = config["configurable"]["settings"]
    llm = LLMClient(settings)

    response = await llm.chat(
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        user_text=_USER_TEXT,
        temperature=0.9,
    )

    if response.finish_reason == "length":
        raise ValueError(
            f"LLM response truncated (finish_reason=length). "
            f"Consider increasing vision_llm_max_tokens (current: {settings.vision_llm_max_tokens})"
        )

    data = LLMClient.extract_json_from_content(response.content)

    # Validate
    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])
    if not (8 <= panel_count <= 12):
        raise ValueError(f"Invalid panel_count: {panel_count}, must be 8-12")
    if len(panels) != panel_count:
        raise ValueError(
            f"panels length ({len(panels)}) != panel_count ({panel_count})"
        )

    logger.info(
        "Script generated: slang='%s', panels=%d",
        data.get("slang", "unknown"), panel_count,
    )

    return {
        "slang": data["slang"],
        "origin": data["origin"],
        "explanation": data["explanation"],
        "panel_count": panel_count,
        "panels": panels,
    }
