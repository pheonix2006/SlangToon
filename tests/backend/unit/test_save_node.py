"""Tests for save_node — LangGraph node for saving comic + history."""

import pytest

from app.nodes.save_node import save_node


def _make_config(settings):
    return {"configurable": {"settings": settings}}


def _make_state(mock_image_gen_b64):
    return {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck",
        "panel_count": 8,
        "comic_prompt": "A comic prompt",
        "image_base64": mock_image_gen_b64,
    }


@pytest.mark.asyncio
async def test_save_node_returns_urls_and_history_id(tmp_data_dir, mock_image_gen_b64):
    """save_node saves image and returns URLs and history_id."""
    from app.config import Settings
    settings = Settings()

    result = await save_node(_make_state(mock_image_gen_b64), _make_config(settings))

    assert "comic_url" in result
    assert "thumbnail_url" in result
    assert "history_id" in result
    assert len(result["history_id"]) > 0


@pytest.mark.asyncio
async def test_save_node_comic_url_starts_with_data_path(tmp_data_dir, mock_image_gen_b64):
    """save_node comic_url starts with /data/comics/."""
    from app.config import Settings
    settings = Settings()

    result = await save_node(_make_state(mock_image_gen_b64), _make_config(settings))

    assert result["comic_url"].startswith("/data/comics/")
