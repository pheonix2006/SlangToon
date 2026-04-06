"""Tests for prompt_node — LangGraph node for comic prompt building."""

import pytest

from app.nodes.prompt_node import prompt_node


def _make_state(panels=None):
    return {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panels": panels or [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
    }


@pytest.mark.asyncio
async def test_prompt_node_returns_comic_prompt():
    """prompt_node returns comic_prompt field."""
    result = await prompt_node(_make_state(), {})
    assert "comic_prompt" in result
    assert isinstance(result["comic_prompt"], str)
    assert len(result["comic_prompt"]) > 0


@pytest.mark.asyncio
async def test_prompt_node_includes_slang_in_prompt():
    """prompt_node output includes slang name."""
    result = await prompt_node(_make_state(), {})
    assert "Break a leg" in result["comic_prompt"]


@pytest.mark.asyncio
async def test_prompt_node_with_12_panels():
    """prompt_node handles 12 panels."""
    panels = [{"scene": f"Scene {i}", "dialogue": ""} for i in range(12)]
    result = await prompt_node(_make_state(panels=panels), {})
    assert "comic_prompt" in result
    assert len(result["comic_prompt"]) > 0
