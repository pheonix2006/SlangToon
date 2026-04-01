"""LLMClient 单元测试 — httpx.AsyncClient 被 mock。"""

from __future__ import annotations

import json
import re

import httpx
import pytest

from app.config import Settings
from app.services.llm_client import (
    LLMClient,
    LLMApiError,
    LLMResponseError,
    LLMTimeoutError,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """构造 Settings 实例。alias 字段必须用 alias 名（大写）传入。"""
    defaults = dict(
        OPENAI_API_KEY="test-key",
        OPENAI_BASE_URL="https://api.example.com/v4",
        OPENAI_MODEL="test-model",
        vision_llm_max_tokens=4096,
        vision_llm_timeout=5,
        vision_llm_max_retries=3,
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# extract_json_from_content
# ---------------------------------------------------------------------------

class TestExtractJson:
    """测试 JSON 提取静态方法。"""

    def test_pure_json(self) -> None:
        raw = json.dumps({"pose": "standing", "confidence": 0.95})
        result = LLMClient.extract_json_from_content(raw)
        assert result == {"pose": "standing", "confidence": 0.95}

    def test_markdown_json_wrapped(self) -> None:
        raw = '```json\n{"pose": "sitting", "confidence": 0.88}\n```'
        result = LLMClient.extract_json_from_content(raw)
        assert result == {"pose": "sitting", "confidence": 0.88}

    def test_markdown_generic_wrapped(self) -> None:
        raw = '```\n{"key": "value"}\n```'
        result = LLMClient.extract_json_from_content(raw)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(LLMResponseError):
            LLMClient.extract_json_from_content("this is not json")

    def test_invalid_json_in_code_block_raises(self) -> None:
        raw = "```json\nnot valid json at all\n```"
        with pytest.raises(LLMResponseError):
            LLMClient.extract_json_from_content(raw)


# ---------------------------------------------------------------------------
# chat_with_vision — 成功调用
# ---------------------------------------------------------------------------

class TestChatWithVision:
    """测试 chat_with_vision（使用 mock）。"""

    def _fake_response(self, content: str, status: int = 200) -> httpx.Response:
        body = json.dumps({
            "choices": [{"message": {"content": content}}],
        })
        resp = httpx.Response(
            status_code=status,
            content=body.encode(),
            request=httpx.Request("POST", "https://example.com"),
        )
        return resp

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        settings = _make_settings()
        client = LLMClient(settings)

        expected_content = '{"pose": "dance", "score": 0.92}'
        fake_resp = self._fake_response(expected_content)

        async def mock_post(*args, **kwargs):
            return fake_resp

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await client.chat_with_vision(
                system_prompt="You are an analyzer.",
                image_base64="aGVsbG8=",
                image_format="jpeg",
                user_text="Describe this.",
            )

        assert result == expected_content

    @pytest.mark.asyncio
    async def test_request_payload_structure(self) -> None:
        """验证发送给 API 的 payload 结构。"""
        settings = _make_settings()
        client = LLMClient(settings)

        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return self._fake_response("ok")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await client.chat_with_vision(
                system_prompt="sys",
                image_base64="abc123",
                image_format="png",
                user_text="analyze",
                temperature=0.5,
            )

        assert captured["url"] == "https://api.example.com/v4/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer test-key"
        payload = captured["json"]
        assert payload["model"] == "test-model"
        assert payload["temperature"] == 0.5
        assert len(payload["messages"]) == 2
        user_msg = payload["messages"][1]
        assert user_msg["role"] == "user"
        # 检查 image_url 部分
        image_part = user_msg["content"][0]
        assert image_part["type"] == "image_url"
        assert image_part["image_url"]["url"] == "data:image/png;base64,abc123"

    @pytest.mark.asyncio
    async def test_base64_with_data_prefix_preserved(self) -> None:
        """如果 base64 已带 data: 前缀，应保留原样。"""
        settings = _make_settings()
        client = LLMClient(settings)

        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return self._fake_response("ok")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await client.chat_with_vision(
                system_prompt="sys",
                image_base64="data:image/jpeg;base64,abc123",
                image_format="jpeg",
                user_text="go",
            )

        image_url = captured["json"]["messages"][1]["content"][0]["image_url"]["url"]
        assert image_url == "data:image/jpeg;base64,abc123"


# ---------------------------------------------------------------------------
# chat_with_vision — 重试逻辑
# ---------------------------------------------------------------------------

class TestRetryLogic:
    """测试重试和错误处理。"""

    def _fake_error_response(self, status: int) -> httpx.Response:
        resp = httpx.Response(
            status_code=status,
            content=b'{"error": "bad"}',
            request=httpx.Request("POST", "https://example.com"),
        )
        return resp

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        """4xx 应立即抛出 LLMApiError，不重试。"""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return self._fake_error_response(400)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(LLMApiError, match="400"):
                await client.chat_with_vision(
                    system_prompt="s",
                    image_base64="x",
                    image_format="jpeg",
                    user_text="u",
                )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_retries_then_raises(self) -> None:
        """超时应重试，耗尽后抛出 LLMTimeoutError。"""
        settings = _make_settings(vision_llm_max_retries=3, vision_llm_timeout=1)
        client = LLMClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(LLMTimeoutError):
                await client.chat_with_vision(
                    system_prompt="s",
                    image_base64="x",
                    image_format="jpeg",
                    user_text="u",
                )

        assert call_count == 3  # 初始调用 + 2 次重试 = max_retries 次

    @pytest.mark.asyncio
    async def test_5xx_retries(self) -> None:
        """5xx 应触发重试，最终成功。"""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = httpx.Response(
                    status_code=500,
                    content=b"server error",
                    request=httpx.Request("POST", "https://example.com"),
                )
                return resp
            # 第三次成功
            body = json.dumps({"choices": [{"message": {"content": "ok"}}]})
            return httpx.Response(
                status_code=200,
                content=body.encode(),
                request=httpx.Request("POST", "https://example.com"),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await client.chat_with_vision(
                system_prompt="s",
                image_base64="x",
                image_format="jpeg",
                user_text="u",
            )

        assert result == "ok"
        assert call_count == 3
