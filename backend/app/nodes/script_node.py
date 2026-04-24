"""Script generation node — LLM call for slang + comic script."""
import logging
from langchain_core.runnables import RunnableConfig
from app.graphs.state import WorkflowState
from app.prompts.script_prompt import build_system_prompt
from app.prompts.theme_packs import get_theme_by_id
from app.services.llm_client import LLMClient
from app.services.script_service import validate_and_finalize
from app.slang_blacklist import SlangBlacklist

logger = logging.getLogger(__name__)

_USER_TEXT = "Generate a random classical idiom and its modern comic script. JSON only."
_BLACKLIST_QUERY_SIZE = 50


async def script_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Call GLM-4.6V to generate random slang + 4 panel comic script."""
    settings = config["configurable"]["settings"]

    # Look up theme world_setting if theme_id is present
    world_setting = ""
    theme_id = state.get("theme_id")
    if theme_id:
        theme = get_theme_by_id(theme_id)
        if theme:
            world_setting = theme["world_setting"]

    blacklist = SlangBlacklist(file_path=settings.slang_blacklist_file)
    recent_slangs = blacklist.get_recent(_BLACKLIST_QUERY_SIZE)
    system_prompt = build_system_prompt(recent_slangs, world_setting=world_setting)

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

    data = validate_and_finalize(response.content, blacklist)

    return {
        "slang": data["slang"],
        "origin": data["origin"],
        "explanation": data["explanation"],
        "panel_count": data["panel_count"],
        "panels": data["panels"],
    }
