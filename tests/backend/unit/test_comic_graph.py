"""Tests for ComicGraph -- end-to-end LangGraph comic generation."""

import pytest

from app.graphs.comic_graph import build_comic_graph


@pytest.mark.asyncio
async def test_comic_graph_produces_urls(tmp_data_dir, mock_image_gen_b64):
    """ComicGraph end-to-end: mock image gen -> verify final state contains URLs."""
    from app.config import Settings
    settings = Settings()

    import unittest.mock as mock
    with mock.patch("app.nodes.comic_node.ImageGenClient") as MockImgClient:
        MockImgClient.return_value.generate_from_text = mock.AsyncMock(
            return_value=mock_image_gen_b64
        )

        graph = build_comic_graph()
        inputs = {
            "slang": "Break a leg",
            "origin": "Western theater",
            "explanation": "Good luck",
            "panel_count": 8,
            "panels": [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
        }
        result = await graph.ainvoke(
            inputs,
            config={"configurable": {"settings": settings}},
        )

    assert "comic_url" in result
    assert "thumbnail_url" in result
    assert "history_id" in result
    assert result["comic_url"].startswith("/data/comics/")
