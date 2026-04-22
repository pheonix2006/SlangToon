"""Tests for OpenRouterProvider — OpenAI-compatible image generation."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.image_gen.base import ImageSize, ImageGenApiError, ImageGenTimeoutError
from app.services.image_gen.openrouter_provider import OpenRouterProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**overrides) -> OpenRouterProvider:
    defaults = dict(
        api_key="sk-or-test-key",
        base_url="https://openrouter.ai/api/v1",
        model="google/gemini-3.1-flash-image-preview",
        timeout=5.0,
        max_retries=3,
    )
    defaults.update(overrides)
    return OpenRouterProvider(**defaults)


def _fake_openrouter_response(
    b64_data: str = "iVBORw0KGgo=",
    content_text: str = "Here is your image.",
) -> httpx.Response:
    """Simulate OpenRouter image generation response."""
    body = json.dumps({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": content_text,
                "images": [{
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_data}"
                    }
                }]
            }
        }]
    })
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://openrouter.ai"))


# ---------------------------------------------------------------------------
# Size conversion
# ---------------------------------------------------------------------------

class TestConvertSize:

    def test_9_16(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1536, 2688))
        assert config["aspect_ratio"] == "9:16"
        assert config["image_size"] == "2K"

    def test_1_1(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1024, 1024))
        assert config["aspect_ratio"] == "1:1"
        assert "image_size" not in config

    def test_16_9(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1344, 768))
        assert config["aspect_ratio"] == "16:9"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestParseResponse:

    def test_with_images(self) -> None:
        p = _make_provider()
        resp = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Done.",
                    "images": [{
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,abc123"}
                    }]
                }
            }]
        }
        assert p._parse_response(resp) == "data:image/png;base64,abc123"

    def test_no_images_raises(self) -> None:
        p = _make_provider()
        resp = {
            "choices": [{
                "message": {"role": "assistant", "content": "No image."}
            }]
        }
        with pytest.raises(ImageGenApiError, match="未返回图片"):
            p._parse_response(resp)

    def test_empty_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"choices": []})

    def test_no_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"error": "something"})


# ---------------------------------------------------------------------------
# generate_from_text
# ---------------------------------------------------------------------------

class TestGenerateFromText:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        p = _make_provider()

        async def mock_post(self_client, url, json=None, headers=None):
            return _fake_openrouter_response("dGVzdA==")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await p.generate_from_text("draw a comic", ImageSize(1536, 2688))

        assert result == "data:image/png;base64,dGVzdA=="

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _fake_openrouter_response()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate_from_text("a comic", ImageSize(1536, 2688))

        assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer sk-or-test-key"

        payload = captured["json"]
        assert payload["model"] == "google/gemini-3.1-flash-image-preview"
        assert payload["modalities"] == ["image", "text"]
        assert payload["image_config"]["aspect_ratio"] == "9:16"
        assert payload["image_config"]["image_size"] == "2K"
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "a comic"

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
    async def test_success(self) -> None:
        p = _make_provider()

        async def mock_post(self_client, url, json=None, headers=None):
            return _fake_openrouter_response("dGVzdA==")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await p.generate(
                "edit this image", "data:image/jpeg;base64,abc123", ImageSize(2688, 1536)
            )

        assert result == "data:image/png;base64,dGVzdA=="

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return _fake_openrouter_response()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate(
                "edit this", "data:image/jpeg;base64,abc123", ImageSize(2688, 1536)
            )

        payload = captured["json"]
        content = payload["messages"][0]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"] == "data:image/jpeg;base64,abc123"
        assert content[1]["type"] == "text"
        assert content[1]["text"] == "edit this"
        assert payload["modalities"] == ["image", "text"]

    @pytest.mark.asyncio
    async def test_ensure_data_url_prefix(self) -> None:
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return _fake_openrouter_response()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate("edit", "raw_base64_no_prefix", ImageSize(1024, 1024))

        content = captured["json"]["messages"][0]["content"]
        assert content[0]["image_url"]["url"] == "data:image/jpeg;base64,raw_base64_no_prefix"
