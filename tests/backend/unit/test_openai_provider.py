"""Tests for OpenAIProvider — OpenAI Images API image generation."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.image_gen.base import ImageSize, ImageGenApiError, ImageGenTimeoutError
from app.services.image_gen.openai_provider import OpenAIProvider


def _make_provider(**overrides) -> OpenAIProvider:
    defaults = dict(
        api_key="sk-test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-image-1",
        timeout=5.0,
        max_retries=3,
    )
    defaults.update(overrides)
    return OpenAIProvider(**defaults)


def _fake_openai_response(b64_data: str = "iVBORw0KGgo=") -> httpx.Response:
    body = json.dumps({"data": [{"b64_json": b64_data}]})
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://api.openai.com"))


def _fake_openai_edit_response(b64_data: str = "iVBORw0KGgo=") -> httpx.Response:
    body = json.dumps({"data": [{"b64_json": b64_data}]})
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://api.openai.com"))


class TestConvertSize:
    def test_16_9(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(2688, 1536)) == "1536x1024"

    def test_1_1(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1024, 1024)) == "1024x1024"

    def test_9_16(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1536, 2688)) == "1024x1536"


class TestParseResponse:
    def test_valid_response(self) -> None:
        p = _make_provider()
        result = p._parse_response({"data": [{"b64_json": "abc123"}]})
        assert result == "data:image/png;base64,abc123"

    def test_empty_data(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError):
            p._parse_response({"data": []})

    def test_missing_data(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError):
            p._parse_response({})


class TestGenerateFromText:
    @pytest.mark.asyncio
    async def test_returns_base64(self) -> None:
        p = _make_provider()
        async def mock_post(self_client, url, **kwargs):
            return _fake_openai_response("test_b64")
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await p.generate_from_text("a cat", ImageSize(1024, 1024))
        assert result == "data:image/png;base64,test_b64"

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        p = _make_provider()
        captured: dict = {}
        async def mock_post(self_client, url, **kwargs):
            captured["json"] = kwargs.get("json")
            return _fake_openai_response()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate_from_text("a cat", ImageSize(2688, 1536))
        payload = captured["json"]
        assert payload["model"] == "gpt-image-1"
        assert payload["prompt"] == "a cat"
        assert payload["size"] == "1536x1024"
        assert payload["response_format"] == "b64_json"


class TestGenerate:
    @pytest.mark.asyncio
    async def test_returns_base64(self) -> None:
        p = _make_provider()
        async def mock_post(self_client, url, **kwargs):
            return _fake_openai_edit_response("edit_b64")
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await p.generate(
                "edit this", "data:image/jpeg;base64,abc123", ImageSize(1024, 1024)
            )
        assert result == "data:image/png;base64,edit_b64"

    @pytest.mark.asyncio
    async def test_ensure_data_url_prefix(self) -> None:
        p = _make_provider()
        captured: dict = {}
        async def mock_post(self_client, url, **kwargs):
            captured["json"] = kwargs.get("json")
            return _fake_openai_edit_response()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate("edit", "raw_base64_no_prefix", ImageSize(1024, 1024))
        payload = captured["json"]
        assert "image" in payload
