"""POST /api/generate-script — Generate random slang + comic script."""

import logging

from fastapi import APIRouter, Depends, Response

from app.config import Settings
from app.dependencies import get_cached_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.script import ScriptRequest, ScriptResponse, Panel
from app.services.llm_client import LLMTimeoutError, LLMApiError, LLMResponseError
from app.tracing.decorators import with_trace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script"])


@router.post(
    "/generate-script",
    response_model=ApiResponse,
    responses={500: {"description": "LLM error"}},
)
@with_trace("script", error_map={
    LLMTimeoutError: (ErrorCode.SCRIPT_LLM_FAILED, "LLM request timeout"),
    LLMApiError: (ErrorCode.SCRIPT_LLM_FAILED, "LLM API error"),
    LLMResponseError: (ErrorCode.SCRIPT_LLM_INVALID, "Invalid LLM response"),
    ValueError: (ErrorCode.SCRIPT_LLM_INVALID, "Invalid script data"),
})
async def generate_script_endpoint(
    request: ScriptRequest = ScriptRequest(),
    settings: Settings = Depends(get_cached_settings),
    response: Response = None,
):
    """Generate a random slang with a 4-10 panel comic script."""
    from app.services.script_service import generate_script

    data = await generate_script(settings)

    response_data = ScriptResponse(
        slang=data["slang"],
        origin=data["origin"],
        explanation=data["explanation"],
        panel_count=data["panel_count"],
        panels=[Panel(**p) for p in data["panels"]],
    )
    return ApiResponse(data=response_data.model_dump())
