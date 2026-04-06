"""Script generation node — LLM call for slang + comic script."""
import logging
from langchain_core.runnables import RunnableConfig
from app.graphs.state import WorkflowState
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT, build_system_prompt
from app.services.llm_client import LLMClient
from app.slang_blacklist import SlangBlacklist

logger = logging.getLogger(__name__)

_USER_TEXT = (
    "Pick a classical idiom, proverb, or traditional saying from any culture "
    "— something with historical depth and cultural resonance. "
    "Reimagine it as a modern comic. Respond with JSON only."
)
_BLACKLIST_QUERY_SIZE = 50


async def script_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Call GLM-4.6V to generate random slang + 8-12 panel comic script.

    Returns: Partial WorkflowState update dict.
    Raises: LLMTimeoutError, LLMApiError, LLMResponseError, ValueError.
    """
    settings = config["configurable"]["settings"]

    # 加载黑名单并构建动态系统提示词
    blacklist = SlangBlacklist(file_path=settings.slang_blacklist_file)
    recent_slangs = blacklist.get_recent(_BLACKLIST_QUERY_SIZE)
    system_prompt = build_system_prompt(recent_slangs)

    llm = LLMClient(settings)

    response = await llm.chat(
        system_prompt=system_prompt,
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

    slang = data["slang"]
    # 成功后将 slang 加入黑名单（失败时不会执行到这里）
    blacklist.add(slang)

    logger.info(
        "Script generated: slang='%s', panels=%d",
        slang,
        panel_count,
    )

    return {
        "slang": slang,
        "origin": data["origin"],
        "explanation": data["explanation"],
        "panel_count": panel_count,
        "panels": panels,
    }
