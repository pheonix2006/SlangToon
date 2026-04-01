import logging

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=ApiResponse)
async def history_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
):
    logger.info("查询历史记录 (page=%d, page_size=%d)", page, page_size)
    history = HistoryService(settings.history_file, settings.max_history_records)
    result = history.get_page(page=page, page_size=page_size)
    logger.info("返回 %d 条历史记录 (total=%d)", len(result["items"]), result["total"])
    return ApiResponse(code=0, message="success", data=result)
