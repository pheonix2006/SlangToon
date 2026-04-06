"""Comic generation node — Qwen Image 2.0 text-to-image."""

import logging

from langchain_core.runnables import RunnableConfig

from app.graphs.state import WorkflowState
from app.services.image_gen_client import ImageGenClient

logger = logging.getLogger(__name__)

COMIC_SIZE = "1536*2688"


async def comic_node(state: WorkflowState, config: RunnableConfig) -> dict:
    """Call Qwen Image 2.0 to generate comic image.

    Returns: {"image_base64": str}
    Raises: ImageGenApiError, ImageGenTimeoutError.
    """
    settings = config["configurable"]["settings"]
    img_client = ImageGenClient(settings)
    image_base64 = await img_client.generate_from_text(
        prompt=state["comic_prompt"],
        size=COMIC_SIZE,
    )
    logger.info("Comic image generated: %d characters", len(image_base64))
    return {"image_base64": image_base64}
