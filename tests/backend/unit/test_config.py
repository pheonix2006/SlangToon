"""Settings 配置类和 get_settings 工厂函数的单元测试。"""

from __future__ import annotations

import pytest

from app.config import Settings, get_settings


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """构造 Settings 实例，禁用 .env 文件读取。"""
    defaults: dict = {}
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


# ---------------------------------------------------------------------------
# test_default_values
# ---------------------------------------------------------------------------

class TestDefaultValues:
    """验证 Settings 的默认值。"""

    def test_default_values(self) -> None:
        s = _make_settings()
        assert s.host == "0.0.0.0"
        assert s.port == 8888
        assert s.debug is False
        assert s.app_name == "SlangToon"
        assert s.app_version == "1.0.0"
        assert s.vision_llm_timeout == 90
        assert s.vision_llm_max_retries == 2
        assert s.qwen_image_timeout == 120
        assert s.max_history_records == 1000


# ---------------------------------------------------------------------------
# test_from_env
# ---------------------------------------------------------------------------

class TestFromEnv:
    """通过环境变量覆盖配置。"""

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOST", "127.0.0.1")
        monkeypatch.setenv("PORT", "9999")
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

        s = Settings(_env_file=None)

        assert s.host == "127.0.0.1"
        assert s.port == 9999
        assert s.debug is True
        assert s.openai_api_key == "sk-test-123"


# ---------------------------------------------------------------------------
# test_cors_origin_list
# ---------------------------------------------------------------------------

class TestCorsOriginList:
    """验证 cors_origin_list 属性。"""

    def test_cors_origin_list(self) -> None:
        s = _make_settings()
        origins = s.cors_origin_list
        assert isinstance(origins, list)
        assert "http://localhost:5173" in origins
        assert "http://localhost:3000" in origins

    def test_cors_origin_list_trims_whitespace(self) -> None:
        s = _make_settings(cors_origins="  a.com , b.com  ")
        assert s.cors_origin_list == ["a.com", "b.com"]


# ---------------------------------------------------------------------------
# test_log_level
# ---------------------------------------------------------------------------

class TestLogLevel:
    """验证 log_level 配置字段。"""

    def test_log_level_default(self) -> None:
        s = _make_settings()
        assert s.log_level == "INFO"

    def test_log_level_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings(_env_file=None)
        assert s.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# test_get_settings
# ---------------------------------------------------------------------------

class TestGetSettings:
    """验证 get_settings 工厂函数。"""

    def test_returns_settings_instance(self) -> None:
        s = get_settings()
        assert isinstance(s, Settings)

    def test_each_call_returns_new_instance(self) -> None:
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is not s2
