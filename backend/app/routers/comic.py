"""POST /api/generate-comic -- Generate comic strip image from script."""

import logging

from fastapi import APIRouter, Depends, Response

from app.config import Settings
from app.dependencies import get_cached_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.comic import ComicRequest, ComicResponse
from app.services.image_gen_client import ImageGenTimeoutError, ImageGenApiError
from app.graphs.trace_collector import GraphExecutionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["comic"])


@router.post(
    "/generate-comic",
    response_model=ApiResponse,
    responses={500: {"description": "Image generation error"}},
)
async def generate_comic_endpoint(
    request: ComicRequest,
    settings: Settings = Depends(get_cached_settings),
    response: Response = None,
):
    """Generate a comic strip image from the script."""
    from app.graphs.comic_graph import build_comic_graph
    from app.graphs.trace_collector import invoke_with_trace
    from app.logging_config import request_id_ctx

    graph = build_comic_graph()
    inputs = request.model_dump()

    def _set_trace_id(tid: str | None):
        if tid and response:
            response.headers["x-trace-id"] = tid

    try:
        result, trace_id = await invoke_with_trace(
            graph,
            inputs,
            settings,
            flow_type="comic",
            request_id=request_id_ctx.get(""),
        )
    except GraphExecutionError as exc:
        _set_trace_id(exc.trace_id)
        original = exc.original_error
        if isinstance(original, (ImageGenTimeoutError, ImageGenApiError)):
            return ApiResponse(code=ErrorCode.IMAGE_GEN_FAILED, message="Image generation error", data=None)
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message="Internal error", data=None)

    _set_trace_id(trace_id)

    response_data = ComicResponse(
        comic_url=result["comic_url"],
        thumbnail_url=result["thumbnail_url"],
        history_id=result["history_id"],
    )
    return ApiResponse(data=response_data.model_dump())
