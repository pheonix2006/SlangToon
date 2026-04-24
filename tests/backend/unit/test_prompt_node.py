"""Tests for prompt_node — LangGraph node for comic prompt building."""

import pytest

from app.nodes.prompt_node import prompt_node


def _make_state(panels=None, **overrides):
    state = {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panels": panels or [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
    }
    state.update(overrides)
    return state


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


@pytest.mark.asyncio
async def test_prompt_node_with_valid_theme_id():
    """prompt_node uses theme's visual_style when theme_id is valid."""
    result = await prompt_node(
        _make_state(theme_id="cyberpunk"), {}
    )
    assert "Neon cyan and magenta lights" in result["comic_prompt"]
    assert "clean manga line art" not in result["comic_prompt"]


@pytest.mark.asyncio
async def test_prompt_node_with_invalid_theme_id():
    """prompt_node falls back to default style when theme_id is not found."""
    result = await prompt_node(
        _make_state(theme_id="nonexistent_theme"), {}
    )
    assert "clean manga line art" in result["comic_prompt"]


@pytest.mark.asyncio
async def test_prompt_node_without_theme_id():
    """prompt_node uses default style when no theme_id in state."""
    result = await prompt_node(_make_state(), {})
    assert "clean manga line art" in result["comic_prompt"]


@pytest.mark.asyncio
async def test_prompt_node_with_empty_theme_id():
    """prompt_node uses default style when theme_id is empty string."""
    result = await prompt_node(
        _make_state(theme_id=""), {}
    )
    assert "clean manga line art" in result["comic_prompt"]
