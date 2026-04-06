"""Tests for script_node — LangGraph node for script generation."""

import json
from unittest.mock import MagicMock, AsyncMock, patch

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


@pytest.mark.asyncio
async def test_script_node_success_adds_to_blacklist(tmp_data_dir):
    """N-01: 成功后 slang 加入黑名单"""
    from app.config import Settings
    settings = Settings()
    mock_data = {
        "slang": "Break a leg", "origin": "Western theater",
        "explanation": "Good luck wish", "panel_count": 8,
        "panels": [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
    }
    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []
    mock_bl.add = MagicMock()
    with patch("app.nodes.script_node.SlangBlacklist") as MockBL, \
         patch("app.nodes.script_node.LLMClient") as MockClient:
        MockBL.return_value = mock_bl
        MockClient.return_value.chat = AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(lambda c: json.loads(c))
        await script_node({"trigger": "ok_gesture"}, _make_config(settings))
    mock_bl.get_recent.assert_called_once_with(50)
    mock_bl.add.assert_called_once_with("Break a leg")


@pytest.mark.asyncio
async def test_script_node_failure_does_not_add_to_blacklist(tmp_data_dir):
    """N-02: 失败时不写入黑名单"""
    from app.config import Settings
    settings = Settings()
    mock_data = {"slang": "Bad", "origin": "T", "explanation": "T",
                 "panel_count": 3, "panels": [{"scene": "A", "dialogue": ""}]}
    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []
    with patch("app.nodes.script_node.SlangBlacklist") as MockBL, \
         patch("app.nodes.script_node.LLMClient") as MockClient:
        MockBL.return_value = mock_bl
        MockClient.return_value.chat = AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(lambda c: json.loads(c))
        with pytest.raises(ValueError, match="Invalid panel_count"):
            await script_node({"trigger": "ok_gesture"}, _make_config(settings))
    mock_bl.add.assert_not_called()


@pytest.mark.asyncio
async def test_script_node_uses_blacklist_in_prompt(tmp_data_dir):
    """N-03: system_prompt 包含历史 slang"""
    from app.config import Settings
    settings = Settings()
    mock_data = {"slang": "New", "origin": "T", "explanation": "T",
                 "panel_count": 8, "panels": [{"scene": f"S{i}", "dialogue": ""} for i in range(8)]}
    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = ["Old A", "Old B"]
    captured = {}
    async def capture(system_prompt, **kw):
        captured["sp"] = system_prompt
        return LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
    with patch("app.nodes.script_node.SlangBlacklist") as MockBL, \
         patch("app.nodes.script_node.LLMClient") as MockClient:
        MockBL.return_value = mock_bl
        MockClient.return_value.chat = capture
        MockClient.extract_json_from_content = staticmethod(lambda c: json.loads(c))
        await script_node({"trigger": "ok_gesture"}, _make_config(settings))
    assert "Old A" in captured["sp"]
    assert "Old B" in captured["sp"]
    assert "ALREADY USED SLANGS" in captured["sp"]


@pytest.mark.asyncio
async def test_script_node_empty_blacklist_uses_base_prompt(tmp_data_dir):
    """N-04: 空黑名单时用原始 prompt"""
    from app.config import Settings
    from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
    settings = Settings()
    mock_data = {"slang": "Fresh", "origin": "T", "explanation": "T",
                 "panel_count": 9, "panels": [{"scene": f"S{i}", "dialogue": ""} for i in range(9)]}
    mock_bl = MagicMock()
    mock_bl.get_recent.return_value = []
    captured = None
    async def capture(system_prompt, **kw):
        nonlocal captured
        captured = system_prompt
        return LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
    with patch("app.nodes.script_node.SlangBlacklist") as MockBL, \
         patch("app.nodes.script_node.LLMClient") as MockClient:
        MockBL.return_value = mock_bl
        MockClient.return_value.chat = capture
        MockClient.extract_json_from_content = staticmethod(lambda c: json.loads(c))
        await script_node({"trigger": "ok_gesture"}, _make_config(settings))
    assert captured == SCRIPT_SYSTEM_PROMPT
    assert "ALREADY USED SLANGS" not in captured
