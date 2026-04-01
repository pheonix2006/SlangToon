"""Trace 查询端点 — 调试用接口。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.flow_log.trace_store import TraceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["traces"])


@router.get("/traces")
async def list_traces(
    date: str | None = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    settings: Settings = Depends(get_settings),
):
    """查询 trace 记录（调试用）。"""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data={"traces": [], "date": date or ""})

    date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    traces = store.query(date=date_str, limit=limit)
    trace_dicts = [t.model_dump() for t in traces]
    return ApiResponse(code=0, message="success", data={"traces": trace_dicts, "date": date_str})
