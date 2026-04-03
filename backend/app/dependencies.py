from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings
from app.flow_log.trace_store import TraceStore
from app.tracing.store import TraceStore as TraceV2Store


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()


def get_trace_store(
    settings: Settings = Depends(get_cached_settings),
) -> TraceStore:
    """TraceStore 依赖，使用缓存的 Settings 避免每次 mkdir。"""
    return TraceStore(settings.trace_dir, settings.trace_retention_days)


def get_trace_v2_store(
    settings: Settings = Depends(get_cached_settings),
) -> TraceV2Store:
    """V2 TraceStore 依赖注入（tracing 模块）。"""
    return TraceV2Store(settings.trace_dir, settings.trace_retention_days)
