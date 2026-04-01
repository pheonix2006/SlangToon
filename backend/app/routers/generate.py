import logging

from fastapi import APIRouter, Depends, Response
from app.schemas.generate import GenerateRequest
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.services.generate_service import generate_artwork, GenerateError
from app.flow_log import FlowSession, NoOpSession, get_current_trace, set_current_trace
from app.flow_log.trace_store import TraceStore
from app.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=ApiResponse)
async def generate_endpoint(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    response: Response = Response(),
):
    logger.info("收到生成请求 (style=%s)", request.style_name)

    # 创建 trace session
    if settings.trace_enabled:
        trace = FlowSession("generate", request_id=request_id_ctx.get(""))
        set_current_trace(trace)
        response.headers["X-Trace-Id"] = trace.trace.trace_id
    else:
        trace = NoOpSession()
        set_current_trace(trace)

    storage = FileStorage(settings.photo_storage_dir, settings.poster_storage_dir)
    history = HistoryService(settings.history_file, settings.max_history_records)
    try:
        result = await generate_artwork(
            request.image_base64, request.image_format,
            request.style_name, request.style_brief,
            settings, storage, history,
        )
        logger.info("生成完成, poster_url=%s", result.get("poster_url", ""))
        if isinstance(trace, FlowSession):
            trace.finish("success")
        return ApiResponse(code=0, message="success", data=result)
    except GenerateError as e:
        logger.error("生成失败: %s", e.message)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("生成异常: %s", e, exc_info=True)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=str(e))
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
    finally:
        if isinstance(trace, FlowSession):
            TraceStore(settings.trace_dir, settings.trace_retention_days).save(trace.trace)
