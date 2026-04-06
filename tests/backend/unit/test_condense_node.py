"""Tests for condense_node — LangGraph node for prompt compression."""

import json
import pytest

from app.nodes.condense_node import condense_node


def _make_config(settings):
    return {"configurable": {"settings": settings}}


def _make_state(prompt="x" * 5000):
    return {"comic_prompt": prompt}


@pytest.mark.asyncio
async def test_condense_node_truncates_on_llm_failure(tmp_data_dir):
    """condense_node falls back to truncation when LLM fails."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.condense_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(side_effect=Exception("LLM down"))

        result = await condense_node(_make_state(), _make_config(settings))

    assert "comic_prompt" in result
    assert isinstance(result["comic_prompt"], str)


@pytest.mark.asyncio
async def test_condense_node_returns_condensed_on_success(tmp_data_dir):
    """condense_node returns new prompt when LLM condense succeeds."""
    from app.config import Settings
    settings = Settings()
    condensed_data = {
        "slang": "Test",
        "origin": "Test",
        "explanation": "Test",
        "panels": [{"scene": "Short", "dialogue": ""}],
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.condense_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=mock.MagicMock(content=json.dumps(condensed_data))
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        result = await condense_node(_make_state(), _make_config(settings))

    assert "comic_prompt" in result


@pytest.mark.asyncio
async def test_condense_node_truncates_on_invalid_llm_response(tmp_data_dir):
    """condense_node falls back to truncation when LLM returns invalid JSON."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.condense_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=mock.MagicMock(content="not json at all")
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        result = await condense_node(_make_state(), _make_config(settings))

    assert "comic_prompt" in result
