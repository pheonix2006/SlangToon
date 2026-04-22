"""Tests for image_gen factory — provider switching."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.image_gen.factory import create_provider
from app.services.image_gen.dashscope_provider import DashScopeProvider
from app.services.image_gen.openrouter_provider import OpenRouterProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        image_gen_provider="dashscope",
        qwen_image_apikey="test-qwen-key",
        qwen_image_base_url="https://dashscope.example.com/api/v1",
        qwen_image_model="qwen-image-2.0",
        openrouter_image_apikey="sk-or-test",
        openrouter_image_base_url="https://openrouter.ai/api/v1",
        openrouter_image_model="google/gemini-3.1-flash-image-preview",
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateProvider:

    def test_default_creates_dashscope(self) -> None:
        settings = _make_settings()  # image_gen_provider defaults to "dashscope"
        provider = create_provider(settings)
        assert isinstance(provider, DashScopeProvider)

    def test_explicit_dashscope(self) -> None:
        settings = _make_settings(image_gen_provider="dashscope")
        provider = create_provider(settings)
        assert isinstance(provider, DashScopeProvider)

    def test_openrouter(self) -> None:
        settings = _make_settings(image_gen_provider="openrouter")
        provider = create_provider(settings)
        assert isinstance(provider, OpenRouterProvider)

    def test_invalid_raises(self) -> None:
        settings = _make_settings(image_gen_provider="invalid_provider")
        with pytest.raises(ValueError, match="invalid_provider"):
            create_provider(settings)

    def test_case_insensitive(self) -> None:
        settings = _make_settings(image_gen_provider="OpenRouter")
        provider = create_provider(settings)
        assert isinstance(provider, OpenRouterProvider)
