"""POST /api/generate-script route integration tests -- LangGraph version."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm_client import LLMClient, LLMResponse


def _mock_llm_client(mock_data):
    """Create mock LLMClient returning specified data."""
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(
        return_value=LLMResponse(content=json.dumps(mock_data), model="test-model")
    )
    return mock_client


@pytest.mark.asyncio
async def test_generate_script_success(client, mock_script_data):
    """Successful script generation returns correct data."""
    mock_client = _mock_llm_client(mock_script_data)

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client), \
         patch("app.nodes.script_node.LLMClient.extract_json_from_content",
               side_effect=lambda c: json.loads(c) if isinstance(c, str) else c):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["slang"] == "Break a leg"
    assert data["data"]["panel_count"] == 8
    assert len(data["data"]["panels"]) == 8


@pytest.mark.asyncio
async def test_generate_script_llm_timeout(client):
    """LLM timeout returns SCRIPT_LLM_FAILED error code."""
    from app.services.llm_client import LLMTimeoutError

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50001  # SCRIPT_LLM_FAILED


@pytest.mark.asyncio
async def test_generate_script_invalid_panel_count(client, mock_script_data):
    """Invalid panel_count returns SCRIPT_LLM_INVALID error code."""
    bad_data = {**mock_script_data, "panel_count": 2, "panels": mock_script_data["panels"][:2]}
    mock_client = _mock_llm_client(bad_data)

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client), \
         patch("app.nodes.script_node.LLMClient.extract_json_from_content",
               side_effect=lambda c: json.loads(c) if isinstance(c, str) else c):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50002  # SCRIPT_LLM_INVALID


@pytest.mark.asyncio
async def test_generate_script_has_trace_id_header(client, mock_script_data):
    """Successful response includes x-trace-id header."""
    mock_client = _mock_llm_client(mock_script_data)

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client), \
         patch("app.nodes.script_node.LLMClient.extract_json_from_content",
               side_effect=lambda c: json.loads(c) if isinstance(c, str) else c):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert "x-trace-id" in resp.headers
    assert resp.headers["x-trace-id"] != ""


@pytest.mark.asyncio
async def test_generate_script_saves_trace(client, mock_script_data, tmp_data_dir):
    """Successful script generation saves trace to JSONL file."""
    mock_client = _mock_llm_client(mock_script_data)

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client), \
         patch("app.nodes.script_node.LLMClient.extract_json_from_content",
               side_effect=lambda c: json.loads(c) if isinstance(c, str) else c):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # Verify trace file
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1, "Should generate at least one trace JSONL file"

    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "script"
    assert trace_data["status"] == "success"
    assert len(trace_data["nodes"]) >= 1


@pytest.mark.asyncio
async def test_generate_script_failed_saves_trace(client, tmp_data_dir):
    """LLM timeout saves failed status trace."""
    from app.services.llm_client import LLMTimeoutError

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

    with patch("app.nodes.script_node.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    assert resp.json()["code"] == 50001

    # Verify trace file exists
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1

    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "script"
    assert trace_data["status"] == "failed"
