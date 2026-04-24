"""POST /api/generate-script -- Generate random slang + comic script."""

import logging

from fastapi import APIRouter, Depends, Response

from app.config import Settings
from app.dependencies import get_cached_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.script import ScriptRequest, ScriptResponse, Panel
from app.services.llm_client import LLMTimeoutError, LLMApiError, LLMResponseError
from app.prompts.theme_packs import get_random_theme
from app.graphs.trace_collector import GraphExecutionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script"])


@router.post(
    "/generate-script",
    response_model=ApiResponse,
    responses={500: {"description": "LLM error"}},
)
async def generate_script_endpoint(
    request: ScriptRequest = ScriptRequest(),
    settings: Settings = Depends(get_cached_settings),
    response: Response = None,
):
    """Generate a random slang with a 8-12 panel comic script."""
    from app.graphs.script_graph import build_script_graph
    from app.graphs.trace_collector import invoke_with_trace
    from app.logging_config import request_id_ctx

    graph = build_script_graph()

    theme = get_random_theme()

    def _set_trace_id(tid: str | None):
        if tid and response:
            response.headers["x-trace-id"] = tid

    try:
        result, trace_id = await invoke_with_trace(
            graph,
            {"trigger": "ok_gesture", "theme_id": theme["id"], "theme_name_zh": theme["name_zh"]},
            settings,
            flow_type="script",
            request_id=request_id_ctx.get(""),
        )
    except GraphExecutionError as exc:
        _set_trace_id(exc.trace_id)
        original = exc.original_error
        if isinstance(original, LLMTimeoutError):
            return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message="LLM request timeout", data=None)
        if isinstance(original, LLMApiError):
            return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message="LLM API error", data=None)
        if isinstance(original, LLMResponseError):
            return ApiResponse(code=ErrorCode.SCRIPT_LLM_INVALID, message="Invalid LLM response", data=None)
        if isinstance(original, ValueError):
            return ApiResponse(code=ErrorCode.SCRIPT_LLM_INVALID, message="Invalid script data", data=None)
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message="Internal error", data=None)

    _set_trace_id(trace_id)

    response_data = ScriptResponse(
        slang=result["slang"],
        origin=result["origin"],
        explanation=result["explanation"],
        panel_count=result["panel_count"],
        panels=[Panel(**p) for p in result["panels"]],
        theme_id=theme["id"],
        theme_name_zh=theme["name_zh"],
    )
    return ApiResponse(data=response_data.model_dump())
