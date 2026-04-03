"""get_cached_settings 和 get_trace_store 依赖函数的单元测试。"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.dependencies import get_cached_settings, get_trace_store
from app.flow_log.trace_store import TraceStore


class TestGetCachedSettings:
    """验证 get_cached_settings 的行为。"""

    def test_returns_settings_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        # 需要清除 lru_cache，确保每次测试都干净
        get_cached_settings.cache_clear()

        result = get_cached_settings()
        assert isinstance(result, Settings)

    def test_returns_same_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        get_cached_settings.cache_clear()

        result1 = get_cached_settings()
        result2 = get_cached_settings()
        assert result1 is result2


class TestGetTraceStore:
    """验证 get_trace_store 依赖函数的行为。"""

    def test_returns_trace_store_instance(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("TRACE_DIR", str(tmp_path))
        get_cached_settings.cache_clear()
        settings = get_cached_settings()

        store = get_trace_store(settings)
        assert isinstance(store, TraceStore)

    def test_uses_settings_trace_config(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: object
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setenv("TRACE_DIR", str(tmp_path))
        monkeypatch.setenv("TRACE_RETENTION_DAYS", "14")
        get_cached_settings.cache_clear()
        settings = get_cached_settings()

        store = get_trace_store(settings)
        assert store.trace_dir == tmp_path
        assert store.retention_days == 14
