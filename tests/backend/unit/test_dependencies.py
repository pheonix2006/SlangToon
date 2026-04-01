"""get_cached_settings 依赖函数的单元测试。"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.dependencies import get_cached_settings


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
