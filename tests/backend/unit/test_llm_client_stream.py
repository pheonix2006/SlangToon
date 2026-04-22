"""LLMClient.chat_stream 单元测试 — 验证 reasoning_content 流式输出。"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

import httpx
import pytest

from app.config import Settings
from app.services.llm_client import (
    LLMClient, StreamChunk, LLMTimeoutError, LLMApiError,
    _extract_reasoning_from_delta,
)


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        OPENAI_API_KEY="test-key",
        OPENAI_BASE_URL="https://api.example.com/v4",
        OPENAI_MODEL="test-model",
        vision_llm_max_tokens=4096,
        vision_llm_timeout=5,
        vision_llm_max_retries=2,
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


class TestStreamChunk:
    def test_thinking_chunk(self):
        c = StreamChunk(type="thinking", text="hello")
        assert c.type == "thinking"
        assert c.text == "hello"

    def test_done_chunk(self):
        c = StreamChunk(type="done", reasoning="think", content="result", usage={"total_tokens": 10})
        assert c.type == "done"
        assert c.reasoning == "think"
        assert c.content == "result"

    def test_defaults(self):
        c = StreamChunk(type="content")
        assert c.text == ""
        assert c.reasoning == ""
        assert c.content == ""
        assert c.usage == {}


class MockStreamResponse:
    def __init__(self, status_code: int, sse_lines: list[str] | None = None, error_body: str = ""):
        self.status_code = status_code
        self._sse_lines = sse_lines or []
        self._error_body = error_body

    async def aiter_lines(self):
        for line in self._sse_lines:
            yield line

    async def aread(self) -> bytes:
        if self._error_body:
            return self._error_body.encode()
        return b""


def _build_thinking_sse_lines(reasoning: str, content: str, usage: dict | None = None) -> list[str]:
    lines: list[str] = []
    for char in reasoning:
        chunk = json.dumps({"choices": [{"delta": {"reasoning_content": char}}]})
        lines.append(f"data: {chunk}")
    for char in content:
        chunk = json.dumps({"choices": [{"delta": {"content": char}}]})
        lines.append(f"data: {chunk}")
    final: dict = {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    if usage:
        final["usage"] = usage
    lines.append(f"data: {json.dumps(final)}")
    lines.append("data: [DONE]")
    return lines


def _make_stream_mock(response):
    @asynccontextmanager
    async def _ctx():
        yield response

    def stream(self, method, url, **kwargs):
        return _ctx()

    return stream


class TestChatStream:
    @pytest.mark.asyncio
    async def test_yields_thinking_and_content_chunks(self):
        settings = _make_settings()
        client = LLMClient(settings)
        usage = {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
        sse = _build_thinking_sse_lines("AB", "CD", usage)
        mock_resp = MockStreamResponse(200, sse)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            chunks = []
            async for chunk in client.chat_stream(system_prompt="sys", user_text="go"):
                chunks.append(chunk)

        thinking_chunks = [c for c in chunks if c.type == "thinking"]
        content_chunks = [c for c in chunks if c.type == "content"]
        done_chunks = [c for c in chunks if c.type == "done"]

        assert len(thinking_chunks) == 2
        assert thinking_chunks[0].text == "A"
        assert thinking_chunks[1].text == "B"
        assert len(content_chunks) == 2
        assert content_chunks[0].text == "C"
        assert content_chunks[1].text == "D"
        assert len(done_chunks) == 1
        assert done_chunks[0].reasoning == "AB"
        assert done_chunks[0].content == "CD"
        assert done_chunks[0].usage == usage

    @pytest.mark.asyncio
    async def test_no_reasoning_content_yields_content_only(self):
        settings = _make_settings()
        client = LLMClient(settings)
        lines = []
        chunk = json.dumps({"choices": [{"delta": {"content": "hello"}}]})
        lines.append(f"data: {chunk}")
        final = json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 5}})
        lines.append(f"data: {final}")
        lines.append("data: [DONE]")
        mock_resp = MockStreamResponse(200, lines)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            chunks = []
            async for c in client.chat_stream(system_prompt="s", user_text="u"):
                chunks.append(c)

        types = [c.type for c in chunks]
        assert "thinking" not in types
        assert types == ["content", "done"]
        assert chunks[-1].reasoning == ""
        assert chunks[-1].content == "hello"

    @pytest.mark.asyncio
    async def test_4xx_raises_immediately(self):
        settings = _make_settings()
        client = LLMClient(settings)
        mock_resp = MockStreamResponse(400, error_body='{"error": "bad request"}')

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            with pytest.raises(LLMApiError, match="400"):
                async for _ in client.chat_stream(system_prompt="s", user_text="u"):
                    pass

    @pytest.mark.asyncio
    async def test_timeout_retries_then_yields_error(self):
        settings = _make_settings(vision_llm_max_retries=2, vision_llm_timeout=1)
        client = LLMClient(settings)
        call_count = 0

        def timeout_stream(self, method, url, **kwargs):
            nonlocal call_count
            call_count += 1

            @asynccontextmanager
            async def _ctx():
                raise httpx.ReadTimeout("timeout")
                yield

            return _ctx()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", timeout_stream)
            chunks = []
            async for c in client.chat_stream(system_prompt="s", user_text="u"):
                chunks.append(c)

        assert call_count == 2
        assert len(chunks) == 1
        assert chunks[0].type == "error"


class TestExtractReasoningFromDelta:
    def test_reasoning_content_field(self):
        delta = {"reasoning_content": "thinking..."}
        assert _extract_reasoning_from_delta(delta) == "thinking..."

    def test_reasoning_string_field(self):
        delta = {"reasoning": "OpenRouter reasoning"}
        assert _extract_reasoning_from_delta(delta) == "OpenRouter reasoning"

    def test_reasoning_details_array(self):
        delta = {"reasoning_details": [
            {"type": "reasoning.text", "text": "step by step"},
        ]}
        assert _extract_reasoning_from_delta(delta) == "step by step"

    def test_reasoning_details_multiple_items(self):
        delta = {"reasoning_details": [
            {"type": "reasoning.text", "text": "part1"},
            {"type": "reasoning.text", "text": "part2"},
        ]}
        assert _extract_reasoning_from_delta(delta) == "part1part2"

    def test_reasoning_details_skips_non_text(self):
        delta = {"reasoning_details": [
            {"type": "reasoning.encrypted", "data": "abc"},
            {"type": "reasoning.text", "text": "visible"},
        ]}
        assert _extract_reasoning_from_delta(delta) == "visible"

    def test_empty_delta(self):
        assert _extract_reasoning_from_delta({}) == ""

    def test_reasoning_content_takes_priority(self):
        delta = {"reasoning_content": "native", "reasoning": "alias"}
        assert _extract_reasoning_from_delta(delta) == "native"


class TestChatStreamOpenRouterFormat:
    @pytest.mark.asyncio
    async def test_reasoning_details_yields_thinking(self):
        settings = _make_settings()
        client = LLMClient(settings)
        lines = []
        chunk1 = json.dumps({"choices": [{"delta": {"reasoning_details": [
            {"type": "reasoning.text", "text": "Let me think"}
        ]}}]})
        lines.append(f"data: {chunk1}")
        chunk2 = json.dumps({"choices": [{"delta": {"content": "result"}}]})
        lines.append(f"data: {chunk2}")
        final = json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 20}})
        lines.append(f"data: {final}")
        lines.append("data: [DONE]")
        mock_resp = MockStreamResponse(200, lines)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "stream", _make_stream_mock(mock_resp))
            chunks = []
            async for c in client.chat_stream(system_prompt="s", user_text="u"):
                chunks.append(c)

        thinking = [c for c in chunks if c.type == "thinking"]
        assert len(thinking) == 1
        assert thinking[0].text == "Let me think"
        done = [c for c in chunks if c.type == "done"]
        assert done[0].reasoning == "Let me think"
        assert done[0].content == "result"
