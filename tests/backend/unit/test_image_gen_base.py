"""Tests for image_gen base module — ImageSize, exceptions, retry."""

from __future__ import annotations

import pytest
import httpx

from app.services.image_gen.base import (
    ImageSize,
    ImageGenApiError,
    ImageGenTimeoutError,
    retry_with_backoff,
)


# ---------------------------------------------------------------------------
# ImageSize
# ---------------------------------------------------------------------------

class TestImageSize:

    def test_creation(self) -> None:
        size = ImageSize(1536, 2688)
        assert size.width == 1536
        assert size.height == 2688

    def test_frozen(self) -> None:
        size = ImageSize(1536, 2688)
        with pytest.raises(AttributeError):
            size.width = 100  # type: ignore[misc]

    def test_aspect_ratio_9_16(self) -> None:
        size = ImageSize(1536, 2688)
        assert size.aspect_ratio == "9:16"

    def test_aspect_ratio_1_1(self) -> None:
        size = ImageSize(1024, 1024)
        assert size.aspect_ratio == "1:1"

    def test_aspect_ratio_16_9(self) -> None:
        size = ImageSize(1344, 768)
        assert size.aspect_ratio == "16:9"

    def test_aspect_ratio_fallback(self) -> None:
        """Non-standard ratio returns w:h simplified."""
        size = ImageSize(1000, 333)
        ratio = size.aspect_ratio
        assert ":" in ratio


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:

    def test_api_error_is_exception(self) -> None:
        exc = ImageGenApiError("test")
        assert isinstance(exc, Exception)
        assert str(exc) == "test"

    def test_timeout_error_is_exception(self) -> None:
        exc = ImageGenTimeoutError("timeout")
        assert isinstance(exc, Exception)
        assert str(exc) == "timeout"


# ---------------------------------------------------------------------------
# retry_with_backoff
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:

    @pytest.mark.asyncio
    async def test_success_first_attempt(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_5xx_then_success(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return httpx.Response(500, content=b'err',
                                      request=httpx.Request("POST", "https://x.com"))
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(400, content=b'bad',
                                  request=httpx.Request("POST", "https://x.com"))

        with pytest.raises(ImageGenApiError, match="400"):
            await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_no_retry(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.raises(ImageGenTimeoutError):
            await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_connect_error_retries(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("refused")
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_exhausted(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, content=b'err',
                                  request=httpx.Request("POST", "https://x.com"))

        with pytest.raises(ImageGenApiError, match="重试"):
            await retry_with_backoff(fn, max_retries=2, backoff_base=0.0)
        assert call_count == 2
