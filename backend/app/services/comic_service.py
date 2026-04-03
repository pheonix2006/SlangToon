"""Comic generation service — build prompt + Qwen Image 2.0."""

import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.prompts.comic_prompt import build_comic_prompt
from app.services.image_gen_client import ImageGenClient
from app.storage.file_storage import FileStorage
from app.tracing.decorators import traceable_node
from app.tracing.models import NodeType

logger = logging.getLogger(__name__)

COMIC_SIZE = "2688*1536"


@traceable_node("generate_comic", node_type=NodeType.CUSTOM)
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
    prompt = build_comic_prompt(
        slang=script_data["slang"],
        origin=script_data["origin"],
        explanation=script_data["explanation"],
        panels=script_data["panels"],
    )

    logger.info(
        "漫画生成中: slang='%s' (prompt=%d 字符)",
        script_data["slang"], len(prompt),
    )

    # Stage 2: Generate image via Qwen Image 2.0 (text-to-image)
    img_client = ImageGenClient(settings)
    image_base64 = await img_client.generate_from_text(prompt=prompt, size=COMIC_SIZE)

    # Stage 3: Save to disk
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
        "slang": script_data["slang"],
        "origin": script_data["origin"],
        "explanation": script_data["explanation"],
        "panel_count": script_data["panel_count"],
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "comic_prompt": prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "history_id": history_id,
    }
