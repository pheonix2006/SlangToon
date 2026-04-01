"""Script generation service — single LLM call for slang + comic script."""

import logging

from app.config import Settings
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


async def generate_script(settings: Settings) -> dict:
    """Generate a random slang + 4-6 panel comic script.

    Returns parsed JSON dict with keys: slang, origin, explanation, panel_count, panels.
    Raises LLMTimeoutError or LLMApiError on failure.
    """
    llm = LLMClient(settings)

    content = await llm.chat(
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        user_text="Please pick a random slang or idiom from any culture and create a comic script for it. Respond with JSON only.",
        temperature=0.9,
    )

    data = LLMClient.extract_json_from_content(content)

    # Validate structure
    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])

    if not (4 <= panel_count <= 6):
        raise ValueError(f"Invalid panel_count: {panel_count}, must be 4-6")
    if len(panels) != panel_count:
        raise ValueError(f"panels length ({len(panels)}) != panel_count ({panel_count})")

    logger.info(
        "Script generated: slang='%s', panels=%d",
        data.get("slang", "unknown"), panel_count,
    )

    return data
