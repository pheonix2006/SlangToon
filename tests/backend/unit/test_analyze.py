import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.analyze_service import analyze_photo, AnalyzeError
from app.services.llm_client import LLMTimeoutError, LLMApiError


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.openai_api_key = "test-key"
    s.openai_base_url = "https://api.test.com/v4"
    s.openai_model = "test-model"
    s.vision_llm_max_tokens = 4096
    s.vision_llm_timeout = 60
    s.vision_llm_max_retries = 3
    return s


@pytest.fixture
def valid_llm_response(mock_llm_options):
    return json.dumps({"options": mock_llm_options})


# ------------------------------------------------------------------
# 正常流程
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_success_returns_5_options(mock_settings, valid_llm_response):
    """正常分析 — 返回 5 个风格选项"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            result = await analyze_photo("fake_b64_data", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[0].name == "主题A"
    assert result[1].brief == "描述B"


@pytest.mark.asyncio
async def test_analyze_options_have_name_and_brief_only(mock_settings, valid_llm_response):
    """返回的 StyleOption 只有 name 和 brief，无 prompt"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    for opt in result:
        assert hasattr(opt, "name")
        assert hasattr(opt, "brief")
        assert not hasattr(opt, "prompt"), "StyleOption 不应包含 prompt 字段"


@pytest.mark.asyncio
async def test_analyze_markdown_wrapped_json(mock_settings, mock_llm_options):
    """LLM 返回 ```json 包裹的 JSON — 应成功解析"""
    wrapped = f"```json\n{json.dumps({'options': mock_llm_options})}\n```"
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=wrapped):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[0].name == "主题A"


# ------------------------------------------------------------------
# 数量校验
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_fewer_than_5_raises_error(mock_settings, mock_llm_options):
    """LLM 返回少于 5 个选项 — 抛异常"""
    short_response = json.dumps({"options": mock_llm_options[:3]})
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=short_response):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "期望 5 个" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_more_than_5_truncates(mock_settings, mock_llm_options):
    """LLM 返回多于 5 个选项 — 只取前 5 个"""
    extra_options = mock_llm_options + [{"name": "多余", "brief": "这个不该出现"}]
    extra_response = json.dumps({"options": extra_options})
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=extra_response):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[4].name != "多余"


# ------------------------------------------------------------------
# LLM 错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_llm_timeout_raises_50001(mock_settings):
    """LLM 超时 — 返回 code 50001"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50001
    assert "Vision LLM 调用失败" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_llm_api_error_raises_50001(mock_settings):
    """LLM API 返回 4xx — 返回 code 50001"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMApiError("401")):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50001


# ------------------------------------------------------------------
# JSON 解析错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_invalid_json_raises_50002(mock_settings):
    """LLM 返回非 JSON — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value="not json"):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002


@pytest.mark.asyncio
async def test_analyze_missing_options_raises_50002(mock_settings):
    """JSON 缺少 options 字段 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"data": []}'):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "缺少 options 字段" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_empty_options_raises_50002(mock_settings):
    """options 为空数组 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"options": []}'):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002


@pytest.mark.asyncio
async def test_analyze_option_not_dict_raises_50002(mock_settings):
    """option 不是字典 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=json.dumps({"options": ["string", {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}]})):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "不是有效对象" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_option_missing_name_raises_50002(mock_settings):
    """option 缺少 name — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=json.dumps({"options": [{"brief": "desc"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}]})):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "name" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_option_empty_brief_raises_50002(mock_settings):
    """option brief 为空 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=json.dumps({"options": [{"name": "主题", "brief": ""}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}, {"name": "a", "brief": "b"}]})):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "brief" in exc_info.value.message


# ------------------------------------------------------------------
# Pydantic 验证
# ------------------------------------------------------------------

def test_analyze_empty_image_rejects(sample_image_base64):
    """空 image_base64 — 422"""
    from pydantic import ValidationError
    from app.schemas.analyze import AnalyzeRequest
    with pytest.raises(ValidationError):
        AnalyzeRequest(image_base64="", image_format="jpeg")


def test_analyze_invalid_format_rejects(sample_image_base64):
    """不支持的格式 — 422"""
    from pydantic import ValidationError
    from app.schemas.analyze import AnalyzeRequest
    with pytest.raises(ValidationError):
        AnalyzeRequest(image_base64=sample_image_base64, image_format="bmp")


# ------------------------------------------------------------------
# Endpoint 测试
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_endpoint_success(client, valid_llm_response, sample_image_base64):
    """POST /api/analyze 正常返回 5 个选项"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            resp = await client.post("/api/analyze", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]["options"]) == 5
    # 确认没有 prompt 字段
    assert "prompt" not in data["data"]["options"][0]


@pytest.mark.asyncio
async def test_analyze_endpoint_llm_error(client, sample_image_base64):
    """LLM 超时 — code 50001, HTTP 200"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            resp = await client.post("/api/analyze", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
            })

    assert resp.status_code == 200
    assert resp.json()["code"] == 50001


@pytest.mark.asyncio
async def test_analyze_endpoint_missing_fields(client):
    """缺少必填字段 — 422"""
    resp = await client.post("/api/analyze", json={"image_format": "jpeg"})
    assert resp.status_code == 422
