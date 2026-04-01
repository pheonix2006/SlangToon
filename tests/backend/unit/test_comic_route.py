"""POST /api/generate-comic 路由集成测试。"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.image_gen_client import ImageGenClient


@pytest.mark.asyncio
async def test_generate_comic_success(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = {
        "slang": mock_script_data["slang"],
        "origin": mock_script_data["origin"],
        "explanation": mock_script_data["explanation"],
        "panel_count": mock_script_data["panel_count"],
        "panels": mock_script_data["panels"],
    }

    with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "comic_url" in data["data"]
    assert "history_id" in data["data"]


@pytest.mark.asyncio
async def test_generate_comic_missing_fields(client):
    resp = await client.post("/api/generate-comic", json={"slang": "test"})
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_generate_comic_api_error(client, mock_script_data):
    from app.services.image_gen_client import ImageGenApiError

    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(
        side_effect=ImageGenApiError("API error")
    )

    request_body = {
        "slang": mock_script_data["slang"],
        "origin": mock_script_data["origin"],
        "explanation": mock_script_data["explanation"],
        "panel_count": mock_script_data["panel_count"],
        "panels": mock_script_data["panels"],
    }

    with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50005  # IMAGE_GEN_FAILED
