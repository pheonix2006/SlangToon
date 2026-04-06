"""POST /api/generate-comic route integration tests -- LangGraph version."""

import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.image_gen_client import ImageGenClient


def _make_comic_request_body(mock_script_data):
    return {
        "slang": mock_script_data["slang"],
        "origin": mock_script_data["origin"],
        "explanation": mock_script_data["explanation"],
        "panel_count": mock_script_data["panel_count"],
        "panels": mock_script_data["panels"],
    }


@pytest.mark.asyncio
async def test_generate_comic_success(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    """Successful comic generation returns correct data."""
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.nodes.comic_node.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "comic_url" in data["data"]
    assert "history_id" in data["data"]


@pytest.mark.asyncio
async def test_generate_comic_missing_fields(client):
    """Missing required fields returns 422."""
    resp = await client.post("/api/generate-comic", json={"slang": "test"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_comic_api_error(client, mock_script_data):
    """ImageGenApiError returns IMAGE_GEN_FAILED error code."""
    from app.services.image_gen_client import ImageGenApiError

    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(
        side_effect=ImageGenApiError("API error")
    )

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.nodes.comic_node.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50005  # IMAGE_GEN_FAILED


@pytest.mark.asyncio
async def test_generate_comic_has_trace_id_header(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    """Successful comic generation includes x-trace-id header."""
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.nodes.comic_node.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert "x-trace-id" in resp.headers
    assert resp.headers["x-trace-id"] != ""


@pytest.mark.asyncio
async def test_generate_comic_saves_trace(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    """Successful comic generation saves trace."""
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.nodes.comic_node.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1

    # Find the comic trace (may be mixed with other traces)
    found_comic = False
    for f in jsonl_files:
        for line in f.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            trace_data = json.loads(line)
            if trace_data.get("flow_type") == "comic":
                assert trace_data["status"] == "success"
                found_comic = True
                break
        if found_comic:
            break
    assert found_comic, "Should find a comic trace record"


@pytest.mark.asyncio
async def test_generate_comic_failed_saves_trace(client, mock_script_data, tmp_data_dir):
    """ImageGenApiError saves failed status trace."""
    from app.services.image_gen_client import ImageGenApiError

    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(
        side_effect=ImageGenApiError("API error")
    )

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.nodes.comic_node.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 50005

    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1

    # Find the failed comic trace
    found_failed = False
    for f in jsonl_files:
        for line in f.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            trace_data = json.loads(line)
            if trace_data.get("flow_type") == "comic" and trace_data.get("status") == "failed":
                found_failed = True
                break
        if found_failed:
            break
    assert found_failed, "Should find a failed comic trace record"
