"""Trace 查询端点 — 调试用接口，支持 V2 过滤和单条查询。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.tracing.store import TraceStore as TraceV2Store
from app.flow_log.trace_store import TraceStore

router = APIRouter(prefix="/api", tags=["traces"])


@router.get("/traces")
async def list_traces(
    date: str | None = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    flow_type: str | None = Query(None, description="按流程类型过滤: script | comic"),
    status: str | None = Query(None, description="按状态过滤: success | failed"),
    settings: Settings = Depends(get_settings),
):
    """查询 trace 记录（调试用），支持 flow_type/status 过滤。"""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data={"traces": [], "date": date or ""})

    date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = TraceV2Store(settings.trace_dir, settings.trace_retention_days)
    traces = store.query(date=date_str, limit=limit, flow_type=flow_type, status=status)
    trace_dicts = [t.model_dump() for t in traces]
    return ApiResponse(code=0, message="success", data={"traces": trace_dicts, "date": date_str})


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    settings: Settings = Depends(get_settings),
):
    """按 trace_id 查询单条 trace 详情。"""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data=None)

    store = TraceV2Store(settings.trace_dir, settings.trace_retention_days)
    trace = store.get_by_trace_id(trace_id)
    if trace is None:
        return ApiResponse(code=40001, message="trace not found", data=None)
    return ApiResponse(code=0, message="success", data=trace.model_dump())
