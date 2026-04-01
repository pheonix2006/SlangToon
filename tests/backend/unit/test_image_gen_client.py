"""ImageGenClient 单元测试 — httpx.AsyncClient 被 mock。"""

from __future__ import annotations

import json
import base64

import httpx
import pytest

from app.config import Settings
from app.services.image_gen_client import (
    ImageGenClient,
    ImageGenApiError,
    ImageGenTimeoutError,
    parse_qwen_image_response,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        qwen_image_apikey="test-img-key",
        qwen_image_base_url="https://dashscope.example.com/api/v1",
        qwen_image_model="qwen-image-2.0",
        qwen_image_timeout=5,
        qwen_image_max_retries=3,
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# parse_qwen_image_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    """测试响应解析。"""

    def test_sync_multimodal_format(self) -> None:
        """同步接口格式: output.choices[0].message.content[0].image"""
        resp = {
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"image": "https://img.example.com/result.png"}
                            ],
                            "role": "assistant",
                        }
                    }
                ]
            }
        }
        result = parse_qwen_image_response(resp)
        assert result == "https://img.example.com/result.png"

    def test_async_task_format(self) -> None:
        """异步任务格式: output.results[0].url"""
        resp = {
            "output": {
                "results": [{"url": "https://dash.example.com/img.png"}],
            }
        }
        result = parse_qwen_image_response(resp)
        assert result == "https://dash.example.com/img.png"

    def test_unknown_format_raises(self) -> None:
        resp = {"unknown_key": "value"}
        with pytest.raises(ImageGenApiError, match="无法解析"):
            parse_qwen_image_response(resp)

    def test_empty_choices_raises(self) -> None:
        resp = {"output": {"choices": []}}
        with pytest.raises(ImageGenApiError, match="无法解析"):
            parse_qwen_image_response(resp)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

class TestGenerate:
    """测试 generate 方法（mock HTTP）。"""

    def _fake_url_response(self, url: str) -> httpx.Response:
        """模拟同步接口返回图片 URL 的响应。"""
        body = json.dumps({
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [{"image": url}],
                            "role": "assistant",
                        }
                    }
                ]
            }
        })
        return httpx.Response(
            status_code=200,
            content=body.encode(),
            request=httpx.Request("POST", "https://example.com"),
        )

    def _fake_error_response(self, status: int, body: str = "error") -> httpx.Response:
        return httpx.Response(
            status_code=status,
            content=body.encode(),
            request=httpx.Request("POST", "https://example.com"),
        )

    @pytest.mark.asyncio
    async def test_successful_response(self) -> None:
        """成功调用应下载图片 URL 并返回 base64。"""
        settings = _make_settings()
        client = ImageGenClient(settings)
        image_url = "https://img.example.com/gen.png"
        image_bytes = b"generated-image-content"

        post_count = 0
        get_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal post_count
            post_count += 1
            return self._fake_url_response(image_url)

        async def mock_get(self_client, url, **kwargs):
            nonlocal get_count
            get_count += 1
            assert url == image_url
            return httpx.Response(
                status_code=200,
                content=image_bytes,
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await client.generate(
                prompt="generate a comic strip",
                image_base64="abc123base64",
            )

        assert post_count == 1
        assert get_count == 1
        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        assert base64.b64decode(b64_part) == image_bytes

    @pytest.mark.asyncio
    async def test_request_payload_structure(self) -> None:
        """验证发送给 API 的 payload 使用正确的 messages 格式。"""
        settings = _make_settings()
        client = ImageGenClient(settings)
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return self._fake_url_response("https://img.example.com/fake.png")

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=b"img",
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await client.generate(
                prompt="a manga-style comic",
                image_base64="rawbase64data",
                image_format="png",
                size="1024*1024",
            )

        assert captured["url"] == "https://dashscope.example.com/api/v1/services/aigc/multimodal-generation/generation"
        assert captured["headers"]["Authorization"] == "Bearer test-img-key"
        payload = captured["json"]
        assert payload["model"] == "qwen-image-2.0"
        assert payload["parameters"]["size"] == "1024*1024"

        # 验证 messages 结构
        messages = payload["input"]["messages"]
        assert len(messages) == 1
        content = messages[0]["content"]
        assert content[0]["image"] == "data:image/png;base64,rawbase64data"
        assert content[1]["text"] == "a manga-style comic"

    @pytest.mark.asyncio
    async def test_base64_with_data_prefix_stripped_in_payload(self) -> None:
        """输入的 base64 如果已有 data: 前缀，应被去除。"""
        settings = _make_settings()
        client = ImageGenClient(settings)
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return self._fake_url_response("https://img.example.com/f.png")

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=b"img",
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await client.generate(
                prompt="p",
                image_base64="data:image/jpeg;base64,abc",
            )

        image_val = captured["json"]["input"]["messages"][0]["content"][0]["image"]
        assert image_val == "data:image/jpeg;base64,abc"

    @pytest.mark.asyncio
    async def test_timeout_no_retry(self) -> None:
        """超时应直接抛出 ImageGenTimeoutError，不重试。"""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenTimeoutError):
                await client.generate(
                    prompt="p",
                    image_base64="x",
                )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_5xx_retries(self) -> None:
        """5xx 应触发重试。"""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0
        image_bytes = b"img"

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return self._fake_error_response(500, "server error")
            return self._fake_url_response("https://img.example.com/ok.png")

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=image_bytes,
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await client.generate(
                prompt="p",
                image_base64="x",
            )

        assert call_count == 3
        assert result.startswith("data:image/png;base64,")

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        """4xx 应直接抛出 ImageGenApiError。"""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return self._fake_error_response(400, "bad request")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenApiError, match="400"):
                await client.generate(
                    prompt="p",
                    image_base64="x",
                )

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_url_response_downloads_and_converts(self) -> None:
        """当 API 返回 URL 时，应下载并转为 base64。"""
        settings = _make_settings()
        client = ImageGenClient(settings)
        image_url = "https://img.example.com/gen.png"
        image_bytes = b"downloaded-image-content"

        post_count = 0
        get_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal post_count
            post_count += 1
            return self._fake_url_response(image_url)

        async def mock_get(self_client, url, **kwargs):
            nonlocal get_count
            get_count += 1
            assert url == image_url
            resp = httpx.Response(
                status_code=200,
                content=image_bytes,
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )
            return resp

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await client.generate(
                prompt="p",
                image_base64="x",
            )

        assert post_count == 1
        assert get_count == 1
        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        assert base64.b64decode(b64_part) == image_bytes


# ---------------------------------------------------------------------------
# generate_from_text — text-to-image
# ---------------------------------------------------------------------------


class TestGenerateFromText:
    """Test text-to-image generation (no reference image)."""

    def _fake_url_response(self, url: str) -> httpx.Response:
        body = json.dumps({
            "output": {
                "choices": [
                    {
                        "message": {
                            "content": [{"image": url}],
                            "role": "assistant",
                        }
                    }
                ]
            }
        })
        return httpx.Response(
            status_code=200,
            content=body.encode(),
            request=httpx.Request("POST", "https://example.com"),
        )

    @pytest.mark.asyncio
    async def test_successful_text_to_image(self) -> None:
        """generate_from_text() should return base64 image data."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        image_url = "https://dash.example.com/comic.png"
        image_bytes = b"comic-image-data"

        async def mock_post(*args, **kwargs):
            return self._fake_url_response(image_url)

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=image_bytes,
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await client.generate_from_text(
                prompt="A 4-panel manga comic strip",
            )

        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        assert base64.b64decode(b64_part) == image_bytes

    @pytest.mark.asyncio
    async def test_text_only_payload_structure(self) -> None:
        """generate_from_text() should NOT include image in payload."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return self._fake_url_response("https://img.example.com/fake.png")

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=b"img",
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await client.generate_from_text(
                prompt="A comic strip",
                size="2688*1536",
            )

        payload = captured["json"]
        # Verify text-only messages content
        msg_content = payload["input"]["messages"][0]["content"]
        assert any(item.get("text") == "A comic strip" for item in msg_content)
        assert not any(item.get("image") for item in msg_content)
        # Verify parameters
        assert payload["parameters"]["size"] == "2688*1536"
        assert payload["parameters"]["prompt_extend"] is False

    @pytest.mark.asyncio
    async def test_text_timeout_raises(self) -> None:
        """Timeout should raise ImageGenTimeoutError without retry."""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenTimeoutError):
                await client.generate_from_text(prompt="test")

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_text_4xx_no_retry(self) -> None:
        """4xx should raise ImageGenApiError without retry."""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return httpx.Response(
                status_code=400,
                content=b'{"error": "bad"}',
                request=httpx.Request("POST", "https://example.com"),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenApiError):
                await client.generate_from_text(prompt="test")

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_text_5xx_retries(self) -> None:
        """5xx should trigger retries."""
        settings = _make_settings(qwen_image_max_retries=3)
        client = ImageGenClient(settings)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return httpx.Response(
                    status_code=500,
                    content=b"server error",
                    request=httpx.Request("POST", "https://example.com"),
                )
            return self._fake_url_response("https://img.example.com/ok.png")

        async def mock_get(self_client, url, **kwargs):
            return httpx.Response(
                status_code=200,
                content=b"img",
                headers={"content-type": "image/png"},
                request=httpx.Request("GET", url),
            )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await client.generate_from_text(prompt="test")

        assert call_count == 3
        assert result.startswith("data:image/png;base64,")
