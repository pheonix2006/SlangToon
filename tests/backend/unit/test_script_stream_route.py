"""POST /api/generate-script-stream SSE 端点测试。"""

import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.llm_client import StreamChunk


def _parse_sse_events(text: str) -> list[dict]:
    """解析 SSE 文本为事件列表 [{event, data}, ...]。"""
    events = []
    current_event = None
    current_data = None
    for line in text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event and current_data:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = None
            current_data = None
    return events


@pytest.mark.asyncio
async def test_stream_success_with_thinking(client, mock_script_data, tmp_data_dir):
    """成功流式生成：thinking + script + done 事件。"""
    content_json = json.dumps(mock_script_data)

    async def mock_chat_stream(system_prompt, user_text, temperature=0.8):
        yield StreamChunk(type="thinking", text="Let me think...")
        yield StreamChunk(type="thinking", text=" about idioms")
        yield StreamChunk(type="content", text=content_json)
        yield StreamChunk(
            type="done",
            reasoning="Let me think... about idioms",
            content=content_json,
            usage={"total_tokens": 100},
        )

    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []

    with patch("app.routers.script_stream.build_script_context") as mock_ctx, \
         patch("app.routers.script_stream.LLMClient") as MockLLM, \
         patch("app.routers.script_stream.validate_and_finalize") as mock_validate:
        mock_ctx.return_value = ("system prompt", mock_bl)
        MockLLM.return_value.chat_stream = mock_chat_stream
        mock_validate.return_value = mock_script_data

        resp = await client.post("/api/generate-script-stream", json={})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "thinking" in event_types
    assert "script" in event_types
    assert "done" in event_types

    script_event = next(e for e in events if e["event"] == "script")
    assert script_event["data"]["slang"] == "Break a leg"


@pytest.mark.asyncio
async def test_stream_no_thinking(client, mock_script_data, tmp_data_dir):
    """模型未产生 thinking 时，只有 script + done。"""
    content_json = json.dumps(mock_script_data)

    async def mock_chat_stream(system_prompt, user_text, temperature=0.8):
        yield StreamChunk(type="content", text=content_json)
        yield StreamChunk(type="done", reasoning="", content=content_json, usage={})

    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []

    with patch("app.routers.script_stream.build_script_context") as mock_ctx, \
         patch("app.routers.script_stream.LLMClient") as MockLLM, \
         patch("app.routers.script_stream.validate_and_finalize") as mock_validate:
        mock_ctx.return_value = ("prompt", mock_bl)
        MockLLM.return_value.chat_stream = mock_chat_stream
        mock_validate.return_value = mock_script_data

        resp = await client.post("/api/generate-script-stream", json={})

    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "thinking" not in event_types
    assert "script" in event_types


@pytest.mark.asyncio
async def test_stream_validation_error(client, tmp_data_dir):
    """校验失败时返回 error 事件。"""
    async def mock_chat_stream(system_prompt, user_text, temperature=0.8):
        yield StreamChunk(type="content", text='{"bad": "data"}')
        yield StreamChunk(type="done", reasoning="", content='{"bad": "data"}', usage={})

    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []

    with patch("app.routers.script_stream.build_script_context") as mock_ctx, \
         patch("app.routers.script_stream.LLMClient") as MockLLM, \
         patch("app.routers.script_stream.validate_and_finalize") as mock_validate:
        mock_ctx.return_value = ("prompt", mock_bl)
        MockLLM.return_value.chat_stream = mock_chat_stream
        mock_validate.side_effect = ValueError("Invalid panel_count: 0")

        resp = await client.post("/api/generate-script-stream", json={})

    events = _parse_sse_events(resp.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["data"]["code"] == 50002
