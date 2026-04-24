"""Script generation shared logic — used by both script_node and script_stream."""

import logging

from app.prompts.script_prompt import build_system_prompt
from app.services.llm_client import LLMClient
from app.slang_blacklist import SlangBlacklist

logger = logging.getLogger(__name__)

_BLACKLIST_QUERY_SIZE = 50


def build_script_context(settings, world_setting: str = "") -> tuple[str, SlangBlacklist]:
    """加载黑名单，构建 system_prompt。"""
    blacklist = SlangBlacklist(file_path=settings.slang_blacklist_file)
    recent_slangs = blacklist.get_recent(_BLACKLIST_QUERY_SIZE)
    system_prompt = build_system_prompt(recent_slangs, world_setting=world_setting)
    return system_prompt, blacklist


def validate_and_finalize(content: str, blacklist: SlangBlacklist) -> dict:
    """JSON 提取 + panel_count/panels 校验 + 加入黑名单。"""
    data = LLMClient.extract_json_from_content(content)

    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])
    if not (3 <= panel_count <= 6):
        raise ValueError(f"Invalid panel_count: {panel_count}, must be 3-6")
    if len(panels) != panel_count:
        raise ValueError(f"panels length ({len(panels)}) != panel_count ({panel_count})")

    slang = data["slang"]
    blacklist.add(slang)
    logger.info("Script validated: slang='%s', panels=%d", slang, panel_count)
    return data
