"""POST /api/generate-script — Generate random slang + comic script."""

import logging

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.script import ScriptRequest, ScriptResponse, Panel
from app.services.llm_client import LLMTimeoutError, LLMApiError, LLMResponseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script"])


@router.post(
    "/generate-script",
    response_model=ApiResponse,
    responses={500: {"description": "LLM error"}},
)
async def generate_script_endpoint(
    request: ScriptRequest = ScriptRequest(),
    settings: Settings = Depends(get_settings),
):
    """Generate a random slang with a 4-6 panel comic script."""
    from app.services.script_service import generate_script

    try:
        data = await generate_script(settings)

        response_data = ScriptResponse(
            slang=data["slang"],
            origin=data["origin"],
            explanation=data["explanation"],
            panel_count=data["panel_count"],
            panels=[Panel(**p) for p in data["panels"]],
        )
        return ApiResponse(data=response_data.model_dump())

    except LLMTimeoutError as e:
        logger.error("Script generation timeout: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message=str(e), data=None)

    except (LLMResponseError, ValueError) as e:
        logger.error("Script generation invalid response: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_INVALID, message=str(e), data=None)

    except LLMApiError as e:
        logger.error("Script generation API error: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message=str(e), data=None)

    except Exception as e:
        logger.exception("Script generation unexpected error")
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
