from functools import lru_cache

from fastapi import Depends

from app.config import Settings, get_settings
from app.graphs.trace_store import TraceStore


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()


def get_trace_store(
    settings: Settings = Depends(get_cached_settings),
) -> TraceStore:
    """TraceStore dependency, uses cached Settings to avoid repeated mkdir."""
    return TraceStore(settings.trace_dir, settings.trace_retention_days)
