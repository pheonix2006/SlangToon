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


@pytest.mark.asyncio
async def test_comic_node_with_reference_image_calls_generate(tmp_data_dir, mock_image_gen_b64):
    """When reference_image is present, comic_node calls generate() instead of generate_from_text()."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.comic_node.ImageGenClient") as MockClient:
        instance = MockClient.return_value
        instance.generate = mock.AsyncMock(return_value=mock_image_gen_b64)
        instance.generate_from_text = mock.AsyncMock(return_value="should_not_be_called")

        state = {
            "comic_prompt": "A 4-panel manga comic strip",
            "reference_image": "data:image/jpeg;base64,abc123",
        }
        result = await comic_node(state, _make_config(settings))

    instance.generate.assert_called_once()
    instance.generate_from_text.assert_not_called()
    assert result["image_base64"] == mock_image_gen_b64


@pytest.mark.asyncio
async def test_comic_node_without_reference_image_calls_generate_from_text(tmp_data_dir, mock_image_gen_b64):
    """When no reference_image, comic_node calls generate_from_text() as before."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.comic_node.ImageGenClient") as MockClient:
        instance = MockClient.return_value
        instance.generate_from_text = mock.AsyncMock(return_value=mock_image_gen_b64)
        instance.generate = mock.AsyncMock(return_value="should_not_be_called")

        state = {"comic_prompt": "A 4-panel manga comic strip"}
        result = await comic_node(state, _make_config(settings))

    instance.generate_from_text.assert_called_once()
    instance.generate.assert_not_called()
    assert result["image_base64"] == mock_image_gen_b64
