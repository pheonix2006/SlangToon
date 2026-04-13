"""LLMClient 单元测试 — mock httpx.AsyncClient.stream 模拟 SSE 流式响应。"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx
import pytest

from app.config import Settings
from app.services.llm_client import (
    LLMClient,
    LLMApiError,
    LLMResponse,
    LLMResponseError,
    LLMTimeoutError,
)


# ---------------------------------------------------------------------------
# helpers — SSE 流式 mock
# ---------------------------------------------------------------------------


class MockStreamResponse:
    """模拟 httpx 流式响应，支持 aiter_lines() 和 aread()。"""

    def __init__(
        self,
        status_code: int,
        sse_lines: list[str] | None = None,
        error_body: str = "",
    ) -> None:
        self.status_code = status_code
        self._sse_lines = sse_lines or []
        self._error_body = error_body

    async def aiter_lines(self):  # type: ignore[override]
        for line in self._sse_lines:
            yield line

    async def aread(self) -> bytes:
        if self._error_body:
            return self._error_body.encode()
        return b"\n".join(line.encode() for line in self._sse_lines)


def _build_sse_lines(
    content: str,
    usage: dict | None = None,
) -> list[str]:
    """构建 OpenAI 兼容的 SSE 行列表。"""
    lines: list[str] = []
    # 内容块
    chunk = json.dumps({"choices": [{"delta": {"content": content}}]})
    lines.append(f"data: {chunk}")
    # 结束块（含 finish_reason + usage）
    final: dict = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    if usage:
        final["usage"] = usage
    lines.append(f"data: {json.dumps(final)}")
    lines.append("data: [DONE]")
    return lines


def _sse_response(
    content: str,
    status: int = 200,
    usage: dict | None = None,
) -> MockStreamResponse:
    """构建成功的 SSE 流式 mock 响应。"""
    default_usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    return MockStreamResponse(
        status,
        sse_lines=_build_sse_lines(content, usage or default_usage),
    )


def _error_response(status: int, body: str = '{"error": "bad"}') -> MockStreamResponse:
    """构建错误 mock 响应（4xx / 5xx）。"""
    return MockStreamResponse(status, error_body=body)


def _make_stream_mock(response, capture: dict | None = None):
    """生成 httpx.AsyncClient.stream 的 mock 函数。

    Args:
        response: MockStreamResponse 实例
        capture: 可选字典，用于捕获请求参数（url, json, headers）
    """

    @asynccontextmanager
    async def _ctx():
        yield response

    def stream(self, method, url, **kwargs):
        if capture is not None:
            capture["url"] = url
            capture["json"] = kwargs.get("json")
            capture["headers"] = kwargs.get("headers")
        return _ctx()

    return stream


def _make_timeout_stream_mock():
    """生成会抛出 httpx.ReadTimeout 的 stream mock。"""

    @asynccontextmanager
    async def _ctx():
        raise httpx.ReadTimeout("timeout")
        yield  # never reached

    def stream(self, method, url, **kwargs):
        return _ctx()

    return stream


# ---------------------------------------------------------------------------
# Settings helper
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
    """测试 chat_with_vision（使用 SSE 流式 mock）。"""

    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        settings = _make_settings()
        client = LLMClient(settings)
        expected_content = '{"pose": "dance", "score": 0.92}'
        mock_resp = _sse_response(expected_content)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            result = await client.chat_with_vision(
                system_prompt="You are an analyzer.",
                image_base64="aGVsbG8=",
                image_format="jpeg",
                user_text="Describe this.",
            )

        assert isinstance(result, LLMResponse)
        assert result.content == expected_content
        assert result.model == "test-model"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.total_tokens == 30
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_request_payload_structure(self) -> None:
        """验证发送给 API 的 payload 结构（含 stream=True）。"""
        settings = _make_settings()
        client = LLMClient(settings)
        captured: dict = {}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                httpx.AsyncClient,
                "stream",
                _make_stream_mock(_sse_response("ok"), capture=captured),
            )
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
        assert payload["stream"] is True  # 流式标志
        assert len(payload["messages"]) == 2
        user_msg = payload["messages"][1]
        assert user_msg["role"] == "user"
        image_part = user_msg["content"][0]
        assert image_part["type"] == "image_url"
        assert image_part["image_url"]["url"] == "data:image/png;base64,abc123"

    @pytest.mark.asyncio
    async def test_base64_with_data_prefix_preserved(self) -> None:
        """如果 base64 已带 data: 前缀，应保留原样。"""
        settings = _make_settings()
        client = LLMClient(settings)
        captured: dict = {}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                httpx.AsyncClient,
                "stream",
                _make_stream_mock(_sse_response("ok"), capture=captured),
            )
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

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        """4xx 应立即抛出 LLMApiError，不重试。"""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0
        mock_resp = _error_response(400)

        def stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            @asynccontextmanager
            async def _ctx():
                yield mock_resp

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", stream)
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

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_timeout_stream_mock())
            # 需要追踪调用次数 — 通过 mock 函数内部追踪
            original_stream = httpx.AsyncClient.stream

            def counting_stream(self, method, url, **kwargs):
                nonlocal call_count
                call_count += 1
                return original_stream(self, method, url, **kwargs)

            # 先设置超时 mock，再包装计数
            mp.setattr(httpx.AsyncClient, "stream", _make_timeout_stream_mock())

            # 使用独立的计数 mock
            call_count = 0

            def counting_timeout_stream(self, method, url, **kwargs):
                nonlocal call_count
                call_count += 1

                @asynccontextmanager
                async def _ctx():
                    raise httpx.ReadTimeout("timeout")
                    yield  # never reached

                return _ctx()

            mp.setattr(httpx.AsyncClient, "stream", counting_timeout_stream)

            with pytest.raises(LLMTimeoutError):
                await client.chat_with_vision(
                    system_prompt="s",
                    image_base64="x",
                    image_format="jpeg",
                    user_text="u",
                )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_5xx_retries(self) -> None:
        """5xx 应触发重试，最终成功。"""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0

        def stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                mock_resp = _error_response(500, "server error")
            else:
                mock_resp = _sse_response("ok")

            @asynccontextmanager
            async def _ctx():
                yield mock_resp

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", stream)
            result = await client.chat_with_vision(
                system_prompt="s",
                image_base64="x",
                image_format="jpeg",
                user_text="u",
            )

        assert isinstance(result, LLMResponse)
        assert result.content == "ok"
        assert call_count == 3


# ---------------------------------------------------------------------------
# chat — text-only call
# ---------------------------------------------------------------------------


class TestChatTextOnly:
    """Test the text-only chat() method (no image, SSE streaming)."""

    @pytest.mark.asyncio
    async def test_successful_text_call(self) -> None:
        """chat() 应通过 SSE 流式接收文本响应。"""
        settings = _make_settings()
        client = LLMClient(settings)
        expected_content = '{"test": true}'
        mock_resp = _sse_response(expected_content)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            result = await client.chat(
                system_prompt="You are a comic writer.",
                user_text="Generate a slang comic script.",
            )

        assert isinstance(result, LLMResponse)
        assert result.content == expected_content
        assert result.model == "test-model"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.total_tokens == 30
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_text_only_payload_structure(self) -> None:
        """Verify chat() sends text-only content (string, not list) + stream=True。"""
        settings = _make_settings()
        client = LLMClient(settings)
        captured: dict = {}

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                httpx.AsyncClient,
                "stream",
                _make_stream_mock(_sse_response("ok"), capture=captured),
            )
            await client.chat(
                system_prompt="sys",
                user_text="hello",
            )

        payload = captured["json"]
        assert payload["model"] == "test-model"
        assert payload["stream"] is True
        user_content = payload["messages"][1]["content"]
        # Text-only: content should be a string, not a list
        assert isinstance(user_content, str)
        assert user_content == "hello"

    @pytest.mark.asyncio
    async def test_text_retries_on_5xx(self) -> None:
        """chat() should retry on 5xx errors."""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0

        def stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                mock_resp = _error_response(500, "server error")
            else:
                mock_resp = _sse_response("ok")

            @asynccontextmanager
            async def _ctx():
                yield mock_resp

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", stream)
            result = await client.chat(system_prompt="sys", user_text="hello")

        assert isinstance(result, LLMResponse)
        assert result.content == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_text_4xx_no_retry(self) -> None:
        """chat() should NOT retry on 4xx errors."""
        settings = _make_settings(vision_llm_max_retries=3)
        client = LLMClient(settings)
        call_count = 0

        def stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            @asynccontextmanager
            async def _ctx():
                yield _error_response(400)

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", stream)
            with pytest.raises(LLMApiError):
                await client.chat(system_prompt="s", user_text="u")

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_text_timeout_raises(self) -> None:
        """chat() should retry on timeout and raise LLMTimeoutError."""
        settings = _make_settings(vision_llm_max_retries=2, vision_llm_timeout=1)
        client = LLMClient(settings)
        call_count = 0

        def counting_timeout_stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            @asynccontextmanager
            async def _ctx():
                raise httpx.ReadTimeout("timeout")
                yield  # never reached

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", counting_timeout_stream)
            with pytest.raises(LLMTimeoutError):
                await client.chat(system_prompt="s", user_text="u")

        assert call_count == 2


# ---------------------------------------------------------------------------
# LLMResponse dataclass
# ---------------------------------------------------------------------------


class TestLLMResponse:
    """Test the LLMResponse dataclass."""

    def test_basic_fields(self) -> None:
        resp = LLMResponse(
            content="hello",
            model="test-model",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
        )
        assert resp.content == "hello"
        assert resp.model == "test-model"
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 20
        assert resp.total_tokens == 30
        assert resp.finish_reason == "stop"

    def test_usage_property(self) -> None:
        resp = LLMResponse(
            content="hello",
            model="test-model",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        assert resp.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    def test_defaults(self) -> None:
        resp = LLMResponse(content="hello", model="test-model")
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0
        assert resp.total_tokens == 0
        assert resp.finish_reason is None
        assert resp.usage == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
