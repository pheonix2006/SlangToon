"""Unit tests for get_cached_settings and get_trace_store dependencies."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.dependencies import get_cached_settings, get_trace_store
from app.graphs.trace_store import TraceStore


class TestGetCachedSettings:
    """Verify get_cached_settings behavior."""

    def test_returns_settings_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "test")
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
    """Verify get_trace_store dependency behavior."""

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
        assert str(store._trace_dir) == str(tmp_path)
        assert store._retention_days == 14
