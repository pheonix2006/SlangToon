"""Script generation service — single LLM call for slang + comic script."""

import logging

from app.config import Settings
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.services.llm_client import LLMClient
from app.tracing.decorators import traceable_node
from app.tracing.models import NodeType

logger = logging.getLogger(__name__)


@traceable_node("generate_script", node_type=NodeType.CUSTOM)
async def generate_script(settings: Settings) -> dict:
    """Generate a random slang + 4-10 panel comic script.

    Returns parsed JSON dict with keys: slang, origin, explanation, panel_count, panels.
    Raises LLMTimeoutError or LLMApiError on failure.
    """
    llm = LLMClient(settings)

    content = await llm.chat(
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        user_text="Pick a classical idiom, proverb, or traditional saying from any culture — something with historical depth and cultural resonance. Reimagine it as a modern comic. Respond with JSON only.",
        temperature=0.9,
    )

    # content is now an LLMResponse; extract the text
    response_text = content.content

    data = LLMClient.extract_json_from_content(response_text)

    # Validate structure
    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])

    if not (4 <= panel_count <= 10):
        raise ValueError(f"Invalid panel_count: {panel_count}, must be 4-10")
    if len(panels) != panel_count:
        raise ValueError(f"panels length ({len(panels)}) != panel_count ({panel_count})")

    logger.info(
        "脚本生成完成: slang='%s', panels=%d",
        data.get("slang", "unknown"), panel_count,
    )

    return data
