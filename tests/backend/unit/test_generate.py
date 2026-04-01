from pathlib import Path

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call

from app.schemas.generate import GenerateRequest
from app.services.generate_service import generate_artwork, GenerateError
from app.services.llm_client import LLMTimeoutError, LLMApiError
from app.services.image_gen_client import ImageGenTimeoutError, ImageGenApiError


# ------------------------------------------------------------------
# Pydantic 验证
# ------------------------------------------------------------------

def test_generate_valid_request(sample_image_base64):
    """有效的 GenerateRequest — 不再需要 prompt"""
    req = GenerateRequest(
        image_base64=sample_image_base64,
        image_format="jpeg",
        style_name="赛博朋克",
        style_brief="霓虹城市中的未来战士",
    )
    assert req.style_name == "赛博朋克"
    assert req.style_brief == "霓虹城市中的未来战士"


def test_generate_missing_style_name(sample_image_base64):
    """缺少 style_name — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            style_brief="desc",
            style_name="",
        )


def test_generate_missing_style_brief(sample_image_base64):
    """缺少 style_brief — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            style_name="赛博朋克",
            style_brief="",
        )


def test_generate_missing_image_base64():
    """image_base64 为空 — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64="",
            style_name="赛博朋克",
            style_brief="desc",
        )


def test_generate_invalid_format(sample_image_base64):
    """不支持的格式 — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="gif",
            style_name="赛博朋克",
            style_brief="desc",
        )


def test_generate_has_no_prompt_field(sample_image_base64):
    """GenerateRequest 不再有 prompt 字段"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            prompt="old field",
            style_name="赛博朋克",
            style_brief="desc",
        )


# ------------------------------------------------------------------
# Service 层：调用顺序
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_calls_llm_compose_then_qwen(client, sample_image_base64, mock_image_gen_b64, mock_compose_response):
    """验证调用顺序：先 LLM compose → 再 Qwen 生图"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None) as mock_llm_init:
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response) as mock_llm_call:
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64) as mock_gen_call:
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "霓虹城市中的未来战士",
                    })

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    # LLM compose 被调用
    assert mock_llm_call.call_count == 1
    # Qwen 生图被调用
    assert mock_gen_call.call_count == 1
    # LLM 在 Qwen 之前调用
    llm_call_args = mock_llm_call.call_args
    assert "赛博朋克" in llm_call_args[0][3]  # user_text 包含 style_name


# ------------------------------------------------------------------
# Service 层：compose 错误处理
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_compose_timeout_raises_50006(client, sample_image_base64):
    """Compose LLM 超时 — code 50006"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50006
    assert "构图设计失败" in data["message"]


@pytest.mark.asyncio
async def test_generate_compose_invalid_json_raises_50007(client, sample_image_base64):
    """Compose LLM 返回无效 JSON — code 50007"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value="not json"):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50007


@pytest.mark.asyncio
async def test_generate_compose_missing_prompt_raises_50007(client, sample_image_base64):
    """Compose LLM 返回 JSON 但缺少 prompt 字段 — code 50007"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"data": "no prompt"}'):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50007


# ------------------------------------------------------------------
# Service 层：Qwen 生图错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_qwen_timeout_raises_50003(client, sample_image_base64, mock_compose_response):
    """Qwen 生图超时 — code 50003"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, side_effect=ImageGenTimeoutError("timeout")):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    assert resp.status_code == 200
    assert resp.json()["code"] == 50003


# ------------------------------------------------------------------
# Service 层：正常流程 + 副作用
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_success_returns_fields(client, sample_image_base64, mock_image_gen_b64, mock_compose_response):
    """正常生成 — 返回 poster_url, thumbnail_url, history_id"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "霓虹城市中的未来战士",
                    })

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["poster_url"].startswith("/data/posters/")
    assert data["thumbnail_url"].startswith("/data/posters/")
    assert "history_id" in data


@pytest.mark.asyncio
async def test_generate_creates_history(client, sample_image_base64, mock_image_gen_b64, mock_compose_response, tmp_data_dir):
    """生成成功后 history 中应有记录"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    assert resp.json()["code"] == 0
    history_id = resp.json()["data"]["history_id"]

    history_resp = await client.get("/api/history")
    history_data = history_resp.json()["data"]
    assert history_data["total"] >= 1
    assert any(item["id"] == history_id for item in history_data["items"])


@pytest.mark.asyncio
async def test_generate_saves_poster_files(client, sample_image_base64, mock_image_gen_b64, mock_compose_response, tmp_data_dir):
    """生成成功后保存海报和缩略图文件"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    data = resp.json()["data"]
    from app.config import get_settings
    settings = get_settings()
    poster_path = Path(settings.poster_storage_dir) / data["poster_url"].replace("/data/posters/", "")
    thumb_path = Path(settings.poster_storage_dir) / data["thumbnail_url"].replace("/data/posters/", "")
    assert poster_path.exists()
    assert thumb_path.exists()


# ------------------------------------------------------------------
# Endpoint 422
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_endpoint_missing_fields(client):
    """缺少必填字段 — 422"""
    resp = await client.post("/api/generate", json={"style_name": "test"})
    assert resp.status_code == 422
