"""Tests for script_node — LangGraph node for script generation."""

import json
import pytest

from app.nodes.script_node import script_node
from app.services.llm_client import LLMResponse


def _make_config(settings):
    return {"configurable": {"settings": settings}}


@pytest.mark.asyncio
async def test_script_node_valid_response_returns_state_update(tmp_data_dir):
    """script_node returns script data on valid LLM response."""
    from app.config import Settings
    settings = Settings()
    mock_data = {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panel_count": 8,
        "panels": [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.script_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=LLMResponse(
                content=json.dumps(mock_data),
                model="glm-4.6v",
            )
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        result = await script_node({"trigger": "ok_gesture"}, _make_config(settings))

    assert result["slang"] == "Break a leg"
    assert result["panel_count"] == 8
    assert len(result["panels"]) == 8


@pytest.mark.asyncio
async def test_script_node_invalid_panel_count_raises_value_error(tmp_data_dir):
    """script_node raises ValueError when panel_count is outside 8-12."""
    from app.config import Settings
    settings = Settings()
    mock_data = {
        "slang": "Test",
        "origin": "Test",
        "explanation": "Test",
        "panel_count": 3,
        "panels": [{"scene": "A", "dialogue": ""}],
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.script_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        with pytest.raises(ValueError, match="Invalid panel_count"):
            await script_node({"trigger": "ok_gesture"}, _make_config(settings))


@pytest.mark.asyncio
async def test_script_node_panel_count_mismatch_raises_value_error(tmp_data_dir):
    """script_node raises ValueError when panels length != panel_count."""
    from app.config import Settings
    settings = Settings()
    mock_data = {
        "slang": "Test",
        "origin": "Test",
        "explanation": "Test",
        "panel_count": 8,
        "panels": [{"scene": "A", "dialogue": ""}],  # only 1 panel
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.script_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        with pytest.raises(ValueError, match="panels length"):
            await script_node({"trigger": "ok_gesture"}, _make_config(settings))


@pytest.mark.asyncio
async def test_script_node_valid_12_panels(tmp_data_dir):
    """script_node accepts 12 panels (upper bound)."""
    from app.config import Settings
    settings = Settings()
    mock_data = {
        "slang": "Test",
        "origin": "Test",
        "explanation": "Test",
        "panel_count": 12,
        "panels": [{"scene": f"S{i}", "dialogue": ""} for i in range(12)],
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.script_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        result = await script_node({"trigger": "ok_gesture"}, _make_config(settings))

    assert result["panel_count"] == 12
    assert len(result["panels"]) == 12
