"""ImageGenClient backward-compatibility tests.

Verifies the thin wrapper delegates correctly and preserves the old interface.
DashScope-specific behavior is tested in test_dashscope_provider.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.services.image_gen_client import (
    ImageGenClient,
    ImageGenApiError,
    ImageGenTimeoutError,
)
from app.services.image_gen.base import ImageSize


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        qwen_image_apikey="test-img-key",
        qwen_image_base_url="https://dashscope.example.com/api/v1",
        qwen_image_model="qwen-image-2.0",
        qwen_image_timeout=5,
        qwen_image_max_retries=3,
        image_gen_provider="dashscope",
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# Import compatibility
# ---------------------------------------------------------------------------

class TestImportCompat:
    """Verify old import paths still work."""

    def test_exceptions_importable(self) -> None:
        from app.services.image_gen_client import ImageGenApiError as E1
        from app.services.image_gen_client import ImageGenTimeoutError as E2
        assert E1 is not None
        assert E2 is not None

    def test_client_importable(self) -> None:
        from app.services.image_gen_client import ImageGenClient as C
        assert C is not None


# ---------------------------------------------------------------------------
# Size parsing
# ---------------------------------------------------------------------------

class TestSizeParsing:

    def test_standard(self) -> None:
        result = ImageGenClient._parse_size("1536*2688")
        assert result == ImageSize(1536, 2688)

    def test_square(self) -> None:
        result = ImageGenClient._parse_size("1024*1024")
        assert result == ImageSize(1024, 1024)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid size"):
            ImageGenClient._parse_size("bad-format")


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

class TestDelegation:

    @pytest.mark.asyncio
    async def test_generate_from_text_delegates(self) -> None:
        """Wrapper delegates to provider.generate_from_text."""
        settings = _make_settings()
        client = ImageGenClient(settings)

        mock_result = "data:image/png;base64,abc123"
        client._provider = AsyncMock()
        client._provider.generate_from_text = AsyncMock(return_value=mock_result)

        result = await client.generate_from_text("draw a cat", size="1536*2688")

        assert result == mock_result
        client._provider.generate_from_text.assert_awaited_once_with(
            "draw a cat", ImageSize(1536, 2688)
        )

    @pytest.mark.asyncio
    async def test_generate_delegates(self) -> None:
        """Wrapper delegates to provider.generate."""
        settings = _make_settings()
        client = ImageGenClient(settings)

        mock_result = "data:image/png;base64,xyz789"
        client._provider = AsyncMock()
        client._provider.generate = AsyncMock(return_value=mock_result)

        result = await client.generate("edit this", "base64data", size="1024*1024")

        assert result == mock_result
        client._provider.generate.assert_awaited_once_with(
            "edit this", "base64data", ImageSize(1024, 1024)
        )

    @pytest.mark.asyncio
    async def test_default_size_generate_from_text(self) -> None:
        """Default size for generate_from_text is 1536*2688."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        client._provider = AsyncMock()
        client._provider.generate_from_text = AsyncMock(return_value="data:image/png;base64,x")

        await client.generate_from_text("prompt")

        client._provider.generate_from_text.assert_awaited_once_with(
            "prompt", ImageSize(1536, 2688)
        )

    @pytest.mark.asyncio
    async def test_default_size_generate(self) -> None:
        """Default size for generate is 1024*1024."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        client._provider = AsyncMock()
        client._provider.generate = AsyncMock(return_value="data:image/png;base64,x")

        await client.generate("prompt", "b64")

        client._provider.generate.assert_awaited_once_with(
            "prompt", "b64", ImageSize(1024, 1024)
        )


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

class TestProviderSelection:

    def test_dashscope_by_default(self) -> None:
        from app.services.image_gen.dashscope_provider import DashScopeProvider
        settings = _make_settings()
        client = ImageGenClient(settings)
        assert isinstance(client._provider, DashScopeProvider)

    def test_openrouter_when_configured(self) -> None:
        from app.services.image_gen.openrouter_provider import OpenRouterProvider
        settings = _make_settings(
            image_gen_provider="openrouter",
            openrouter_image_apikey="sk-or-test",
        )
        client = ImageGenClient(settings)
        assert isinstance(client._provider, OpenRouterProvider)
