import logging

from fastapi import APIRouter, Depends, Response
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.services.analyze_service import analyze_photo, AnalyzeError
from app.flow_log import FlowSession, NoOpSession, get_current_trace, set_current_trace
from app.flow_log.trace_store import TraceStore
from app.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=ApiResponse)
async def analyze_endpoint(
    request: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
    response: Response = Response(),
):
    logger.info("收到分析请求")

    # 创建 trace session
    if settings.trace_enabled:
        trace = FlowSession("analyze", request_id=request_id_ctx.get(""))
        set_current_trace(trace)
        response.headers["X-Trace-Id"] = trace.trace.trace_id
    else:
        trace = NoOpSession()
        set_current_trace(trace)

    try:
        options = await analyze_photo(request.image_base64, request.image_format, settings)
        logger.info("分析完成, 返回 %d 个风格选项", len(options))
        if isinstance(trace, FlowSession):
            trace.finish("success")
        return ApiResponse(code=0, message="success", data=AnalyzeResponse(options=options).model_dump())
    except AnalyzeError as e:
        logger.error("分析失败: %s", e.message)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("分析异常: %s", e, exc_info=True)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=str(e))
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
    finally:
        if isinstance(trace, FlowSession):
            TraceStore(settings.trace_dir, settings.trace_retention_days).save(trace.trace)
