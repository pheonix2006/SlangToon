"""POST /api/generate-comic — Generate comic strip image from script."""

import logging

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.comic import ComicRequest, ComicResponse
from app.services.image_gen_client import (
    ImageGenTimeoutError,
    ImageGenApiError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["comic"])


@router.post(
    "/generate-comic",
    response_model=ApiResponse,
    responses={500: {"description": "Image generation error"}},
)
async def generate_comic_endpoint(
    request: ComicRequest,
    settings: Settings = Depends(get_settings),
):
    """Generate a 16:9 comic strip image from the script."""
    from app.services.comic_service import generate_comic

    script_data = request.model_dump()

    try:
        data = await generate_comic(script_data, settings)

        response_data = ComicResponse(
            comic_url=data["comic_url"],
            thumbnail_url=data["thumbnail_url"],
            history_id=data["history_id"],
        )
        return ApiResponse(data=response_data.model_dump())

    except ImageGenTimeoutError as e:
        logger.error("Comic generation timeout: %s", e)
        return ApiResponse(code=ErrorCode.IMAGE_GEN_FAILED, message=str(e), data=None)

    except ImageGenApiError as e:
        logger.error("Comic generation API error: %s", e)
        return ApiResponse(code=ErrorCode.IMAGE_GEN_FAILED, message=str(e), data=None)

    except Exception as e:
        logger.exception("Comic generation unexpected error")
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
