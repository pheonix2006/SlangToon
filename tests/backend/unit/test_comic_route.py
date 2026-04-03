"""POST /api/generate-comic 路由集成测试。"""

import json

import pytest
from pathlib import Path
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


# ── FlowSession trace 集成测试 ─────────────────────────────────


def _make_comic_request_body(mock_script_data):
    """构造 /api/generate-comic 请求体。"""
    return {
        "slang": mock_script_data["slang"],
        "origin": mock_script_data["origin"],
        "explanation": mock_script_data["explanation"],
        "panel_count": mock_script_data["panel_count"],
        "panels": mock_script_data["panels"],
    }


@pytest.mark.asyncio
async def test_generate_comic_has_trace_id_header(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    """成功生成漫画时，响应应包含 x-trace-id 响应头。"""
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    assert "x-trace-id" in resp.headers
    assert resp.headers["x-trace-id"] != ""


@pytest.mark.asyncio
async def test_generate_comic_trace_has_generate_step(client, mock_script_data, mock_image_gen_b64, tmp_data_dir):
    """成功生成漫画时，trace 应记录 flow_type=comic, status=success，且 @traceable_node 生成 generate_comic 步骤。"""
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()

    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    # 验证 trace 文件
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1, "应至少生成一个 trace JSONL 文件"

    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "comic"
    assert trace_data["status"] == "success"

    # 查找 generate_comic 步骤（由 @traceable_node 装饰器创建）
    gen_steps = [s for s in trace_data["steps"] if s["name"] == "generate_comic"]
    assert len(gen_steps) == 1, "应有一个 generate_comic 步骤"
    step = gen_steps[0]
    assert step["status"] == "success"
    assert step["node_type"] == "custom"


@pytest.mark.asyncio
async def test_generate_comic_failed_saves_trace(client, mock_script_data, tmp_data_dir):
    """ImageGenApiError 时，应保存 failed 状态的 trace。"""
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()

    from app.services.image_gen_client import ImageGenApiError

    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(
        side_effect=ImageGenApiError("API error")
    )

    request_body = _make_comic_request_body(mock_script_data)

    with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
        resp = await client.post("/api/generate-comic", json=request_body)

    assert resp.status_code == 200
    assert resp.json()["code"] == 50005  # IMAGE_GEN_FAILED

    # 验证 trace 文件存在
    trace_dir = tmp_data_dir / "traces"
    jsonl_files = list(trace_dir.glob("*.jsonl"))
    assert len(jsonl_files) >= 1, "失败时也应保存 trace 文件"

    last_line = jsonl_files[0].read_text(encoding="utf-8").strip().split("\n")[-1]
    trace_data = json.loads(last_line)
    assert trace_data["flow_type"] == "comic"
    assert trace_data["status"] == "failed"
