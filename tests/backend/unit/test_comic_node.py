"""Tests for comic_node — LangGraph node for image generation."""

import pytest

from app.nodes.comic_node import comic_node


def _make_config(settings):
    return {"configurable": {"settings": settings}}


def _make_state():
    return {"comic_prompt": "A 8-panel manga comic strip"}


@pytest.mark.asyncio
async def test_comic_node_returns_image_base64(tmp_data_dir, mock_image_gen_b64):
    """comic_node calls ImageGenClient and returns base64 image."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.comic_node.ImageGenClient") as MockClient:
        instance = MockClient.return_value
        instance.generate_from_text = mock.AsyncMock(return_value=mock_image_gen_b64)

        result = await comic_node(_make_state(), _make_config(settings))

    assert "image_base64" in result
    assert result["image_base64"] == mock_image_gen_b64
