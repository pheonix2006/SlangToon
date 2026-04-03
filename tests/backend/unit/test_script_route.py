"""POST /api/generate-script 路由集成测试。"""

import json
import pytest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm_client import LLMClient, LLMResponse


@pytest.mark.asyncio
async def test_generate_script_success(client, mock_script_data):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=LLMResponse(content=json.dumps(mock_script_data), model="test-model"))

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.script_service.LLMClient", return_value=mock_client)
        )
        stack.enter_context(
            patch(
                "app.services.script_service.LLMClient.extract_json_from_content",
                side_effect=lambda content: json.loads(content),
            )
        )
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["slang"] == "Break a leg"
    assert data["data"]["panel_count"] == 4
    assert len(data["data"]["panels"]) == 4


@pytest.mark.asyncio
async def test_generate_script_llm_timeout(client):
    from app.services.llm_client import LLMTimeoutError

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

    with patch("app.services.script_service.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50001  # SCRIPT_LLM_FAILED


@pytest.mark.asyncio
async def test_generate_script_invalid_response(client, mock_script_data):
    """When LLM returns invalid panel_count, should return SCRIPT_LLM_INVALID."""
    bad_data = {**mock_script_data, "panel_count": 2, "panels": mock_script_data["panels"][:2]}
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=LLMResponse(content=json.dumps(bad_data), model="test-model"))

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.script_service.LLMClient", return_value=mock_client)
        )
        stack.enter_context(
            patch(
                "app.services.script_service.LLMClient.extract_json_from_content",
                side_effect=lambda content: json.loads(content),
            )
        )
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50002  # SCRIPT_LLM_INVALID


# ── FlowSession trace 集成测试 ─────────────────────────────────


@pytest.mark.asyncio
async def test_generate_script_saves_trace(client, mock_script_data, tmp_data_dir):
    """成功生成脚本时，应保存 trace 到 JSONL 文件。"""
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=LLMResponse(content=json.dumps(mock_script_data), model="test-model"))

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.script_service.LLMClient", return_value=mock_client)
        )
        stack.enter_context(
            patch(
                "app.services.script_service.LLMClient.extract_json_from_content",
                side_effect=lambda content: json.loads(content),
            )
        )
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 验证 trace 文件存在
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1, "应至少生成一个 trace JSONL 文件"

    # 解析最后一行 JSON
    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "script"
    assert trace_data["status"] == "success"
    assert len(trace_data["steps"]) >= 1


@pytest.mark.asyncio
async def test_generate_script_has_trace_id_header(client, mock_script_data):
    """成功响应应包含 x-trace-id 响应头。"""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=LLMResponse(content=json.dumps(mock_script_data), model="test-model"))

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.services.script_service.LLMClient", return_value=mock_client)
        )
        stack.enter_context(
            patch(
                "app.services.script_service.LLMClient.extract_json_from_content",
                side_effect=lambda content: json.loads(content),
            )
        )
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert "x-trace-id" in resp.headers
    assert resp.headers["x-trace-id"] != ""


@pytest.mark.asyncio
async def test_generate_script_failed_saves_trace(client, tmp_data_dir):
    """LLM 超时时，应保存 failed 状态的 trace。"""
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()

    from app.services.llm_client import LLMTimeoutError

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

    with patch("app.services.script_service.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert resp.json()["code"] == 50001

    # 验证 trace 文件存在
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1, "失败时也应保存 trace 文件"

    # 解析最后一行 JSON
    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "script"
    assert trace_data["status"] == "failed"
    assert any(s["status"] == "failed" for s in trace_data["steps"])
