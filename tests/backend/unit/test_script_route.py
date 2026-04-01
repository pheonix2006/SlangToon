"""POST /api/generate-script 路由集成测试。"""

import json
import pytest
from contextlib import ExitStack
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm_client import LLMClient


@pytest.mark.asyncio
async def test_generate_script_success(client, mock_script_data):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=json.dumps(mock_script_data))

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
    mock_client.chat = AsyncMock(return_value=json.dumps(bad_data))

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
