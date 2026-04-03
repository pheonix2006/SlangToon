"""POST /api/generate-comic — Generate comic strip image from script."""

import logging

from fastapi import APIRouter, Depends, Response

from app.config import Settings
from app.dependencies import get_cached_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.comic import ComicRequest, ComicResponse
from app.services.image_gen_client import (
    ImageGenTimeoutError,
    ImageGenApiError,
)
from app.tracing.decorators import with_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["comic"])


@router.post(
    "/generate-comic",
    response_model=ApiResponse,
    responses={500: {"description": "Image generation error"}},
)
@with_trace("comic", error_map={
    ImageGenTimeoutError: (ErrorCode.IMAGE_GEN_FAILED, "Image generation timeout"),
    ImageGenApiError: (ErrorCode.IMAGE_GEN_FAILED, "Image generation error"),
})
async def generate_comic_endpoint(
    request: ComicRequest,
    settings: Settings = Depends(get_cached_settings),
    response: Response = None,
):
    """Generate a 16:9 comic strip image from the script."""
    from app.services.comic_service import generate_comic

    data = await generate_comic(request.model_dump(), settings)

    response_data = ComicResponse(
        comic_url=data["comic_url"],
        thumbnail_url=data["thumbnail_url"],
        history_id=data["history_id"],
    )
    return ApiResponse(data=response_data.model_dump())
