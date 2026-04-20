"""Tests for DashScopeProvider — extracted from existing image_gen_client."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.services.image_gen.base import ImageSize, ImageGenApiError, ImageGenTimeoutError
from app.services.image_gen.dashscope_provider import DashScopeProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**overrides) -> DashScopeProvider:
    defaults = dict(
        api_key="test-key",
        base_url="https://dashscope.example.com/api/v1",
        model="qwen-image-2.0",
        timeout=5.0,
        max_retries=3,
    )
    defaults.update(overrides)
    return DashScopeProvider(**defaults)


def _fake_dashscope_response(image_url: str) -> httpx.Response:
    """Simulate DashScope sync API response with image URL."""
    body = json.dumps({
        "output": {
            "choices": [{
                "message": {
                    "content": [{"image": image_url}],
                    "role": "assistant",
                }
            }]
        }
    })
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://example.com"))


def _fake_image_download(content: bytes = b"png-bytes",
                         content_type: str = "image/png") -> httpx.Response:
    return httpx.Response(200, content=content,
                          headers={"content-type": content_type},
                          request=httpx.Request("GET", "https://example.com"))


# ---------------------------------------------------------------------------
# Size conversion
# ---------------------------------------------------------------------------

class TestConvertSize:

    def test_standard_size(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1536, 2688)) == "1536*2688"

    def test_square_size(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1024, 1024)) == "1024*1024"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestParseResponse:

    def test_sync_format(self) -> None:
        p = _make_provider()
        resp = {
            "output": {
                "choices": [{"message": {"content": [{"image": "https://img.com/a.png"}]}}]
            }
        }
        assert p._parse_response(resp) == "https://img.com/a.png"

    def test_async_format(self) -> None:
        p = _make_provider()
        resp = {"output": {"results": [{"url": "https://img.com/b.png"}]}}
        assert p._parse_response(resp) == "https://img.com/b.png"

    def test_invalid_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"unknown": "data"})

    def test_empty_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"output": {"choices": []}})


# ---------------------------------------------------------------------------
# generate_from_text
# ---------------------------------------------------------------------------

class TestGenerateFromText:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Full flow: POST → parse URL → download → base64."""
        p = _make_provider()
        image_url = "https://img.example.com/comic.png"
        image_bytes = b"comic-image-data"

        async def mock_post(self_client, url, json=None, headers=None):
            return _fake_dashscope_response(image_url)

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download(image_bytes)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await p.generate_from_text("test prompt", ImageSize(1536, 2688))

        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        assert base64.b64decode(b64_part) == image_bytes

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        """Verify DashScope-specific payload format."""
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _fake_dashscope_response("https://img.example.com/f.png")

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await p.generate_from_text("a comic", ImageSize(1536, 2688))

        assert captured["url"].endswith("/services/aigc/multimodal-generation/generation")
        assert captured["headers"]["Authorization"] == "Bearer test-key"
        payload = captured["json"]
        assert payload["model"] == "qwen-image-2.0"
        assert payload["parameters"]["size"] == "1536*2688"
        assert payload["parameters"]["prompt_extend"] is False
        msg = payload["input"]["messages"][0]
        assert msg["content"][0]["text"] == "a comic"

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        p = _make_provider(max_retries=3)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenTimeoutError):
                await p.generate_from_text("test", ImageSize(1024, 1024))
        assert call_count == 1


# ---------------------------------------------------------------------------
# generate (image-to-image)
# ---------------------------------------------------------------------------

class TestGenerate:

    @pytest.mark.asyncio
    async def test_image_payload_structure(self) -> None:
        """Verify image-to-image payload includes image content."""
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return _fake_dashscope_response("https://img.example.com/f.png")

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await p.generate("prompt", "rawbase64", ImageSize(1024, 1024))

        content = captured["json"]["input"]["messages"][0]["content"]
        assert content[0]["image"] == "data:image/jpeg;base64,rawbase64"
        assert content[1]["text"] == "prompt"
