"""Comic generation service — build prompt + Qwen Image 2.0."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.prompts.comic_prompt import build_comic_prompt, count_tokens, _truncate_prompt_to_tokens, MAX_PROMPT_TOKENS
from app.services.image_gen_client import ImageGenClient
from app.storage.file_storage import FileStorage
from app.tracing.decorators import image_gen_node

logger = logging.getLogger(__name__)

COMIC_SIZE = "2688*1536"


async def _condense_via_llm(prompt: str, settings: Settings) -> str | None:
    """Try to condense the prompt via LLM. Returns condensed prompt or None on failure."""
    from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
    from app.services.llm_client import LLMClient

    llm = LLMClient(settings)
    try:
        content = await llm.chat(
            system_prompt=CONDENSE_SYSTEM_PROMPT,
            user_text=prompt,
            temperature=0.3,
        )
        condensed = LLMClient.extract_json_from_content(content)
        if condensed and "panels" in condensed:
            # Rebuild prompt from condensed script data
            condensed_prompt = build_comic_prompt(
                slang=condensed.get("slang", ""),
                origin=condensed.get("origin", ""),
                explanation=condensed.get("explanation", ""),
                panels=condensed["panels"],
            )
            return condensed_prompt
        logger.warning("LLM condense returned invalid structure, falling back to truncation")
        return None
    except Exception as exc:
        logger.warning("LLM condense failed, falling back to truncation: %s", exc)
        return None


@image_gen_node("generate_comic")
async def generate_comic(script_data: dict, settings: Settings) -> dict:
    """Generate a comic strip image from script data.

    Args:
        script_data: Dict with keys slang, origin, explanation, panel_count, panels.
        settings: Application settings.

    Returns:
        Dict with comic_url, thumbnail_url, history_id.

    Raises:
        ImageGenApiError, ImageGenTimeoutError on failure.
    """
    # Stage 1: Build visual prompt
    current_prompt = build_comic_prompt(
        slang=script_data["slang"],
        origin=script_data["origin"],
        explanation=script_data["explanation"],
        panels=script_data["panels"],
    )
    current_data = script_data

    token_count = count_tokens(current_prompt)

    logger.info(
        "漫画生成中: slang='%s' (prompt=%d 字符, %d tokens)",
        script_data["slang"], len(current_prompt), token_count,
    )

    # Stage 2: Token limit check — condense if over MAX_PROMPT_TOKENS
    if token_count > MAX_PROMPT_TOKENS:
        original_count = token_count
        logger.warning(
            "Prompt exceeds token limit (%d > %d), attempting LLM condense",
            original_count, MAX_PROMPT_TOKENS,
        )
        condensed = await _condense_via_llm(current_prompt, settings)
        if condensed:
            current_prompt = condensed
            token_count = count_tokens(current_prompt)
            logger.info("LLM condense succeeded: %d -> %d tokens", original_count, token_count)

        # Final safety check after condense
        if token_count > MAX_PROMPT_TOKENS:
            current_prompt = _truncate_prompt_to_tokens(current_prompt, MAX_PROMPT_TOKENS)
            logger.warning(
                "Prompt force truncated to %d tokens",
                MAX_PROMPT_TOKENS,
            )

    # Stage 3: Generate image via Qwen Image 2.0 (text-to-image)
    img_client = ImageGenClient(settings)
    image_base64 = await img_client.generate_from_text(prompt=current_prompt, size=COMIC_SIZE)

    # Stage 4: Save to disk
    history_id = uuid.uuid4().hex
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    storage = FileStorage(settings.comic_storage_dir)
    urls = storage.save_comic(image_base64, history_id, date_str)

    logger.info("漫画已保存: history_id=%s, url=%s", history_id, urls["comic_url"])

    # Save to history
    from app.services.history_service import HistoryService
    history_svc = HistoryService(settings.history_file, settings.max_history_records)
    history_svc.add({
        "id": history_id,
        "slang": current_data["slang"],
        "origin": current_data["origin"],
        "explanation": current_data["explanation"],
        "panel_count": current_data["panel_count"],
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "comic_prompt": current_prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "history_id": history_id,
    }
