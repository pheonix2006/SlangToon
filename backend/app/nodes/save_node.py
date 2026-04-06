"""Save node — persist comic to disk + history records."""

import logging
import uuid
from datetime import datetime, timezone

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)


async def save_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Save comic image to disk and write history record.

    Returns: {"comic_url": str, "thumbnail_url": str, "history_id": str}
    """
    settings = config["configurable"]["settings"]

    history_id = uuid.uuid4().hex
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    storage = FileStorage(settings.comic_storage_dir)
    urls = storage.save_comic(state["image_base64"], history_id, date_str)

    logger.info("Comic saved: history_id=%s, url=%s", history_id, urls["comic_url"])

    # Save history record
    history_svc = HistoryService(settings.history_file, settings.max_history_records)
    history_svc.add({
        "id": history_id,
        "slang": state["slang"],
        "origin": state["origin"],
        "explanation": state["explanation"],
        "panel_count": state["panel_count"],
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "comic_prompt": state["comic_prompt"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "history_id": history_id,
    }
