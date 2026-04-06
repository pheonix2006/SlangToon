"""Trace query endpoints -- using new TraceStore."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.graphs.trace_store import TraceStore

router = APIRouter(prefix="/api", tags=["traces"])


@router.get("/traces")
async def list_traces(
    date: str | None = Query(None, description="Date YYYY-MM-DD, defaults to today"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    flow_type: str | None = Query(None, description="Filter by flow type: script | comic"),
    status: str | None = Query(None, description="Filter by status: success | failed"),
    settings: Settings = Depends(get_settings),
):
    """Query trace records (debug), supports flow_type/status filtering."""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data={"traces": [], "date": date or ""})

    date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    traces = store.query(date=date_str, limit=limit, flow_type=flow_type, status=status)
    trace_dicts = [t.model_dump() for t in traces]
    return ApiResponse(code=0, message="success", data={"traces": trace_dicts, "date": date_str})


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    settings: Settings = Depends(get_settings),
):
    """Query a single trace by trace_id."""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data=None)

    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    trace = store.get_by_trace_id(trace_id)
    if trace is None:
        return ApiResponse(code=40001, message="trace not found", data=None)
    return ApiResponse(code=0, message="success", data=trace.model_dump())
