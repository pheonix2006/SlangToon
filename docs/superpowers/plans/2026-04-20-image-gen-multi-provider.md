# Image Gen Multi-Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support switching between DashScope and OpenRouter image generation backends via `.env` config, without breaking existing Qwen functionality.

**Architecture:** Strategy pattern — `ImageGenProvider` Protocol with two implementations (`DashScopeProvider`, `OpenRouterProvider`), a factory function for instantiation, and a backward-compatible `ImageGenClient` wrapper that preserves all existing import paths and call signatures.

**Tech Stack:** Python 3.12, FastAPI, httpx, pydantic-settings, pytest + pytest-asyncio

---

### Task 1: base.py — Exceptions, ImageSize, retry utility

**Files:**
- Create: `backend/app/services/image_gen/__init__.py`
- Create: `backend/app/services/image_gen/base.py`
- Create: `tests/backend/unit/test_image_gen_base.py`

- [ ] **Step 1: Create empty package**

Create the `image_gen` directory with an empty `__init__.py`:

```python
# backend/app/services/image_gen/__init__.py
```

- [ ] **Step 2: Write failing tests for base.py**

Create `tests/backend/unit/test_image_gen_base.py`:

```python
"""Tests for image_gen base module — ImageSize, exceptions, retry."""

from __future__ import annotations

import pytest
import httpx

from app.services.image_gen.base import (
    ImageSize,
    ImageGenApiError,
    ImageGenTimeoutError,
    retry_with_backoff,
)


# ---------------------------------------------------------------------------
# ImageSize
# ---------------------------------------------------------------------------

class TestImageSize:

    def test_creation(self) -> None:
        size = ImageSize(1536, 2688)
        assert size.width == 1536
        assert size.height == 2688

    def test_frozen(self) -> None:
        size = ImageSize(1536, 2688)
        with pytest.raises(AttributeError):
            size.width = 100  # type: ignore[misc]

    def test_aspect_ratio_9_16(self) -> None:
        size = ImageSize(1536, 2688)
        assert size.aspect_ratio == "9:16"

    def test_aspect_ratio_1_1(self) -> None:
        size = ImageSize(1024, 1024)
        assert size.aspect_ratio == "1:1"

    def test_aspect_ratio_16_9(self) -> None:
        size = ImageSize(1344, 768)
        assert size.aspect_ratio == "16:9"

    def test_aspect_ratio_fallback(self) -> None:
        """Non-standard ratio returns w:h simplified."""
        size = ImageSize(1000, 333)
        ratio = size.aspect_ratio
        assert ":" in ratio


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestExceptions:

    def test_api_error_is_exception(self) -> None:
        exc = ImageGenApiError("test")
        assert isinstance(exc, Exception)
        assert str(exc) == "test"

    def test_timeout_error_is_exception(self) -> None:
        exc = ImageGenTimeoutError("timeout")
        assert isinstance(exc, Exception)
        assert str(exc) == "timeout"


# ---------------------------------------------------------------------------
# retry_with_backoff
# ---------------------------------------------------------------------------

class TestRetryWithBackoff:

    @pytest.mark.asyncio
    async def test_success_first_attempt(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_5xx_then_success(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return httpx.Response(500, content=b'err',
                                      request=httpx.Request("POST", "https://x.com"))
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(400, content=b'bad',
                                  request=httpx.Request("POST", "https://x.com"))

        with pytest.raises(ImageGenApiError, match="400"):
            await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_no_retry(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.raises(ImageGenTimeoutError):
            await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_connect_error_retries(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("refused")
            return httpx.Response(200, content=b'ok',
                                  request=httpx.Request("POST", "https://x.com"))

        resp = await retry_with_backoff(fn, max_retries=3, backoff_base=0.0)
        assert resp.status_code == 200
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_exhausted(self) -> None:
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, content=b'err',
                                  request=httpx.Request("POST", "https://x.com"))

        with pytest.raises(ImageGenApiError, match="重试"):
            await retry_with_backoff(fn, max_retries=2, backoff_base=0.0)
        assert call_count == 2
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_base.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.image_gen.base'`

- [ ] **Step 4: Implement base.py**

Create `backend/app/services/image_gen/base.py`:

```python
"""Image generation shared types, exceptions, and retry logic."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from math import gcd
from typing import Any, Awaitable, Callable, Protocol

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ImageGenApiError(Exception):
    """图像生成 API 返回错误。"""


class ImageGenTimeoutError(Exception):
    """图像生成请求超时。"""


# ---------------------------------------------------------------------------
# ImageSize
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageSize:
    """统一的图像尺寸表示，各 provider 自行转换为平台格式。"""

    width: int
    height: int

    @property
    def aspect_ratio(self) -> str:
        """返回简化的宽高比字符串，如 '9:16'。"""
        d = gcd(self.width, self.height)
        return f"{self.width // d}:{self.height // d}"


# ---------------------------------------------------------------------------
# Provider Protocol
# ---------------------------------------------------------------------------

class ImageGenProvider(Protocol):
    """图像生成 provider 统一接口。"""

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 格式字符串。"""
        ...

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 格式字符串。"""
        ...


# ---------------------------------------------------------------------------
# Shared retry logic
# ---------------------------------------------------------------------------

async def retry_with_backoff(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> httpx.Response:
    """统一重试逻辑：5xx/连接错误重试，4xx 直接抛出，超时不重试。

    返回成功的 httpx.Response（2xx/3xx）。
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = await fn()

            if resp.status_code >= 500:
                last_exc = ImageGenApiError(
                    f"API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                )
                logger.debug("5xx (attempt %d/%d): %s", attempt, max_retries, last_exc)
                if attempt < max_retries:
                    await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
                continue

            if resp.status_code >= 400:
                raise ImageGenApiError(
                    f"API 客户端错误 {resp.status_code}: {resp.text[:500]}"
                )

            return resp

        except httpx.TimeoutException as exc:
            raise ImageGenTimeoutError(
                f"请求超时: {exc}"
            ) from exc

        except (ImageGenApiError, ImageGenTimeoutError):
            raise

        except httpx.ConnectError as exc:
            last_exc = exc
            logger.debug("连接错误 (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))

        except Exception as exc:
            last_exc = exc
            logger.debug("请求异常 (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))

    raise ImageGenApiError(
        f"请求在 {max_retries} 次重试后仍然失败"
    ) from last_exc
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_base.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/image_gen/__init__.py backend/app/services/image_gen/base.py tests/backend/unit/test_image_gen_base.py
git commit -m "feat(image-gen): add base module with ImageSize, exceptions, retry"
```

---

### Task 2: dashscope_provider.py — Extract existing DashScope logic

**Files:**
- Create: `backend/app/services/image_gen/dashscope_provider.py`
- Create: `tests/backend/unit/test_dashscope_provider.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/unit/test_dashscope_provider.py`:

```python
"""Tests for DashScopeProvider — extracted from existing image_gen_client."""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.services.image_gen.base import ImageSize, ImageGenApiError, ImageGenTimeoutError
from app.services.image_gen.dashscope_provider import DashScopeProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**overrides) -> DashScopeProvider:
    defaults = dict(
        api_key="test-key",
        base_url="https://dashscope.example.com/api/v1",
        model="qwen-image-2.0",
        timeout=5.0,
        max_retries=3,
    )
    defaults.update(overrides)
    return DashScopeProvider(**defaults)


def _fake_dashscope_response(image_url: str) -> httpx.Response:
    """Simulate DashScope sync API response with image URL."""
    body = json.dumps({
        "output": {
            "choices": [{
                "message": {
                    "content": [{"image": image_url}],
                    "role": "assistant",
                }
            }]
        }
    })
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://example.com"))


def _fake_image_download(content: bytes = b"png-bytes",
                         content_type: str = "image/png") -> httpx.Response:
    return httpx.Response(200, content=content,
                          headers={"content-type": content_type},
                          request=httpx.Request("GET", "https://example.com"))


# ---------------------------------------------------------------------------
# Size conversion
# ---------------------------------------------------------------------------

class TestConvertSize:

    def test_standard_size(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1536, 2688)) == "1536*2688"

    def test_square_size(self) -> None:
        p = _make_provider()
        assert p._convert_size(ImageSize(1024, 1024)) == "1024*1024"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestParseResponse:

    def test_sync_format(self) -> None:
        p = _make_provider()
        resp = {
            "output": {
                "choices": [{"message": {"content": [{"image": "https://img.com/a.png"}]}}]
            }
        }
        assert p._parse_response(resp) == "https://img.com/a.png"

    def test_async_format(self) -> None:
        p = _make_provider()
        resp = {"output": {"results": [{"url": "https://img.com/b.png"}]}}
        assert p._parse_response(resp) == "https://img.com/b.png"

    def test_invalid_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"unknown": "data"})

    def test_empty_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"output": {"choices": []}})


# ---------------------------------------------------------------------------
# generate_from_text
# ---------------------------------------------------------------------------

class TestGenerateFromText:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Full flow: POST → parse URL → download → base64."""
        p = _make_provider()
        image_url = "https://img.example.com/comic.png"
        image_bytes = b"comic-image-data"

        async def mock_post(self_client, url, json=None, headers=None):
            return _fake_dashscope_response(image_url)

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download(image_bytes)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            result = await p.generate_from_text("test prompt", ImageSize(1536, 2688))

        assert result.startswith("data:image/png;base64,")
        b64_part = result.split(",", 1)[1]
        assert base64.b64decode(b64_part) == image_bytes

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        """Verify DashScope-specific payload format."""
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _fake_dashscope_response("https://img.example.com/f.png")

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await p.generate_from_text("a comic", ImageSize(1536, 2688))

        assert captured["url"].endswith("/services/aigc/multimodal-generation/generation")
        assert captured["headers"]["Authorization"] == "Bearer test-key"
        payload = captured["json"]
        assert payload["model"] == "qwen-image-2.0"
        assert payload["parameters"]["size"] == "1536*2688"
        assert payload["parameters"]["prompt_extend"] is False
        msg = payload["input"]["messages"][0]
        assert msg["content"][0]["text"] == "a comic"

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        p = _make_provider(max_retries=3)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenTimeoutError):
                await p.generate_from_text("test", ImageSize(1024, 1024))
        assert call_count == 1


# ---------------------------------------------------------------------------
# generate (image-to-image)
# ---------------------------------------------------------------------------

class TestGenerate:

    @pytest.mark.asyncio
    async def test_image_payload_structure(self) -> None:
        """Verify image-to-image payload includes image content."""
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["json"] = json
            return _fake_dashscope_response("https://img.example.com/f.png")

        async def mock_get(self_client, url, **kwargs):
            return _fake_image_download()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            mp.setattr(httpx.AsyncClient, "get", mock_get)
            await p.generate("prompt", "rawbase64", ImageSize(1024, 1024))

        content = captured["json"]["input"]["messages"][0]["content"]
        assert content[0]["image"] == "data:image/jpeg;base64,rawbase64"
        assert content[1]["text"] == "prompt"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/backend/unit/test_dashscope_provider.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement dashscope_provider.py**

Create `backend/app/services/image_gen/dashscope_provider.py`:

```python
"""DashScope (Qwen Image 2.0) provider implementation."""

from __future__ import annotations

import base64
import logging

import httpx

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)


class DashScopeProvider:
    """基于 DashScope 同步接口的图像生成 provider。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]}
                ]
            },
            "parameters": {
                "n": 1,
                "size": self._convert_size(size),
                "prompt_extend": False,
            },
        }
        logger.info("DashScope 文生图 (model=%s)", self._model)
        data = await self._request(payload)
        image_url = self._parse_response(data)
        return await self._download_as_base64(image_url)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 字符串。"""
        clean_b64 = self._strip_data_prefix(image_base64)
        image_data_url = f"data:image/jpeg;base64,{clean_b64}"

        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_data_url},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {
                "n": 1,
                "size": self._convert_size(size),
            },
        }
        logger.info("DashScope 图生图 (model=%s)", self._model)
        data = await self._request(payload)
        image_url = self._parse_response(data)
        return await self._download_as_base64(image_url)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_size(size: ImageSize) -> str:
        """ImageSize → DashScope 格式 'WxH'。"""
        return f"{size.width}*{size.height}"

    @staticmethod
    def _parse_response(api_response: dict) -> str:
        """解析 DashScope 响应，提取图片 URL。

        支持同步格式 (output.choices) 和异步格式 (output.results)。
        """
        output = api_response.get("output", {})
        if isinstance(output, dict):
            # 同步格式: output.choices[0].message.content[0].image
            choices = output.get("choices", [])
            if isinstance(choices, list) and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", [])
                if isinstance(content, list) and len(content) > 0:
                    image_url = content[0].get("image", "")
                    if image_url:
                        return image_url

            # 异步格式: output.results[0].url
            results = output.get("results", [])
            if isinstance(results, list) and len(results) > 0:
                first = results[0]
                if isinstance(first, dict) and "url" in first:
                    return first["url"]

        raise ImageGenApiError(
            f"无法解析 DashScope 响应格式: {list(api_response.keys())}"
        )

    async def _request(self, payload: dict) -> dict:
        """发送请求到 DashScope，使用共享重试逻辑。"""
        url = f"{self._base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async def _do_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.post(url, json=payload, headers=headers)

        resp = await retry_with_backoff(
            _do_request,
            max_retries=self._max_retries,
            backoff_base=1.0,
        )
        return resp.json()

    async def _download_as_base64(self, image_url: str) -> str:
        """下载远程图片并转为 base64 data URL。"""
        logger.info("下载图片: %s", image_url[:100])
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/png")
                b64 = base64.b64encode(resp.content).decode("ascii")
                logger.info("图片下载完成 (%d bytes)", len(resp.content))
                return f"data:{content_type};base64,{b64}"
        except httpx.HTTPStatusError as exc:
            raise ImageGenApiError(
                f"图片下载失败 (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ImageGenTimeoutError(
                f"图片下载超时 ({self._timeout}s)"
            ) from exc

    @staticmethod
    def _strip_data_prefix(data: str) -> str:
        """去除 data:image/...;base64, 前缀。"""
        prefix = "data:image/"
        idx = data.find(prefix)
        if idx != -1:
            comma = data.find(",", idx)
            if comma != -1:
                return data[comma + 1:]
        return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/backend/unit/test_dashscope_provider.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_gen/dashscope_provider.py tests/backend/unit/test_dashscope_provider.py
git commit -m "feat(image-gen): add DashScopeProvider extracted from existing client"
```

---

### Task 3: openrouter_provider.py — New OpenRouter implementation

**Files:**
- Create: `backend/app/services/image_gen/openrouter_provider.py`
- Create: `tests/backend/unit/test_openrouter_provider.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/unit/test_openrouter_provider.py`:

```python
"""Tests for OpenRouterProvider — OpenAI-compatible image generation."""

from __future__ import annotations

import json

import httpx
import pytest

from app.services.image_gen.base import ImageSize, ImageGenApiError, ImageGenTimeoutError
from app.services.image_gen.openrouter_provider import OpenRouterProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_provider(**overrides) -> OpenRouterProvider:
    defaults = dict(
        api_key="sk-or-test-key",
        base_url="https://openrouter.ai/api/v1",
        model="google/gemini-3.1-flash-image-preview",
        timeout=5.0,
        max_retries=3,
    )
    defaults.update(overrides)
    return OpenRouterProvider(**defaults)


def _fake_openrouter_response(
    b64_data: str = "iVBORw0KGgo=",
    content_text: str = "Here is your image.",
) -> httpx.Response:
    """Simulate OpenRouter image generation response."""
    body = json.dumps({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": content_text,
                "images": [{
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64_data}"
                    }
                }]
            }
        }]
    })
    return httpx.Response(200, content=body.encode(),
                          request=httpx.Request("POST", "https://openrouter.ai"))


# ---------------------------------------------------------------------------
# Size conversion
# ---------------------------------------------------------------------------

class TestConvertSize:

    def test_9_16(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1536, 2688))
        assert config["aspect_ratio"] == "9:16"
        assert config["image_size"] == "2K"

    def test_1_1(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1024, 1024))
        assert config["aspect_ratio"] == "1:1"
        assert "image_size" not in config

    def test_16_9(self) -> None:
        p = _make_provider()
        config = p._convert_size(ImageSize(1344, 768))
        assert config["aspect_ratio"] == "16:9"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestParseResponse:

    def test_with_images(self) -> None:
        p = _make_provider()
        resp = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Done.",
                    "images": [{
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,abc123"}
                    }]
                }
            }]
        }
        assert p._parse_response(resp) == "data:image/png;base64,abc123"

    def test_no_images_raises(self) -> None:
        p = _make_provider()
        resp = {
            "choices": [{
                "message": {"role": "assistant", "content": "No image."}
            }]
        }
        with pytest.raises(ImageGenApiError, match="未返回图片"):
            p._parse_response(resp)

    def test_empty_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"choices": []})

    def test_no_choices_raises(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="无法解析"):
            p._parse_response({"error": "something"})


# ---------------------------------------------------------------------------
# generate_from_text
# ---------------------------------------------------------------------------

class TestGenerateFromText:

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        p = _make_provider()

        async def mock_post(self_client, url, json=None, headers=None):
            return _fake_openrouter_response("dGVzdA==")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            result = await p.generate_from_text("draw a comic", ImageSize(1536, 2688))

        assert result == "data:image/png;base64,dGVzdA=="

    @pytest.mark.asyncio
    async def test_payload_structure(self) -> None:
        p = _make_provider()
        captured: dict = {}

        async def mock_post(self_client, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _fake_openrouter_response()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            await p.generate_from_text("a comic", ImageSize(1536, 2688))

        assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer sk-or-test-key"

        payload = captured["json"]
        assert payload["model"] == "google/gemini-3.1-flash-image-preview"
        assert payload["modalities"] == ["image", "text"]
        assert payload["image_config"]["aspect_ratio"] == "9:16"
        assert payload["image_config"]["image_size"] == "2K"
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "a comic"

    @pytest.mark.asyncio
    async def test_timeout_raises(self) -> None:
        p = _make_provider(max_retries=3)
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("timeout")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(httpx.AsyncClient, "post", mock_post)
            with pytest.raises(ImageGenTimeoutError):
                await p.generate_from_text("test", ImageSize(1024, 1024))
        assert call_count == 1


# ---------------------------------------------------------------------------
# generate (image-to-image) — not supported
# ---------------------------------------------------------------------------

class TestGenerate:

    @pytest.mark.asyncio
    async def test_raises_not_supported(self) -> None:
        p = _make_provider()
        with pytest.raises(ImageGenApiError, match="not support"):
            await p.generate("prompt", "base64data", ImageSize(1024, 1024))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/backend/unit/test_openrouter_provider.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement openrouter_provider.py**

Create `backend/app/services/image_gen/openrouter_provider.py`:

```python
"""OpenRouter provider — OpenAI-compatible image generation."""

from __future__ import annotations

import logging

import httpx

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

# 大尺寸阈值：总像素 > 1K 默认分辨率 (1024*1024) 视为 2K
_2K_PIXEL_THRESHOLD = 1024 * 1024 + 1


class OpenRouterProvider:
    """基于 OpenRouter OpenAI 兼容接口的图像生成 provider。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        payload: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": self._convert_size(size),
        }
        logger.info("OpenRouter 文生图 (model=%s)", self._model)
        data = await self._request(payload)
        return self._parse_response(data)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — OpenRouter 不支持，抛出异常。"""
        raise ImageGenApiError(
            "OpenRouter does not support image-to-image generation"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_size(size: ImageSize) -> dict:
        """ImageSize → OpenRouter image_config dict。"""
        config: dict = {"aspect_ratio": size.aspect_ratio}
        if size.width * size.height > _2K_PIXEL_THRESHOLD:
            config["image_size"] = "2K"
        return config

    @staticmethod
    def _parse_response(api_response: dict) -> str:
        """解析 OpenRouter 响应，提取 base64 data URL。

        格式: choices[0].message.images[0].image_url.url
        """
        choices = api_response.get("choices", [])
        if not choices:
            raise ImageGenApiError(
                f"无法解析 OpenRouter 响应: {list(api_response.keys())}"
            )

        message = choices[0].get("message", {})
        images = message.get("images", [])
        if not images:
            raise ImageGenApiError(
                "OpenRouter 未返回图片，请确认模型支持图像生成且 modalities 参数正确"
            )

        return images[0]["image_url"]["url"]

    async def _request(self, payload: dict) -> dict:
        """发送请求到 OpenRouter，使用共享重试逻辑。"""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async def _do_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.post(url, json=payload, headers=headers)

        resp = await retry_with_backoff(
            _do_request,
            max_retries=self._max_retries,
            backoff_base=1.0,
        )
        return resp.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/backend/unit/test_openrouter_provider.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_gen/openrouter_provider.py tests/backend/unit/test_openrouter_provider.py
git commit -m "feat(image-gen): add OpenRouterProvider for OpenAI-compatible image gen"
```

---

### Task 4: factory.py + __init__.py — Assembly and public API

**Files:**
- Create: `backend/app/services/image_gen/factory.py`
- Modify: `backend/app/services/image_gen/__init__.py`
- Modify: `backend/app/config.py`
- Create: `tests/backend/unit/test_image_gen_factory.py`

- [ ] **Step 1: Write failing tests**

Create `tests/backend/unit/test_image_gen_factory.py`:

```python
"""Tests for image_gen factory — provider switching."""

from __future__ import annotations

import os

import pytest

from app.config import Settings
from app.services.image_gen.factory import create_provider
from app.services.image_gen.dashscope_provider import DashScopeProvider
from app.services.image_gen.openrouter_provider import OpenRouterProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    defaults = dict(
        qwen_image_apikey="test-qwen-key",
        qwen_image_base_url="https://dashscope.example.com/api/v1",
        qwen_image_model="qwen-image-2.0",
        openrouter_image_apikey="sk-or-test",
        openrouter_image_base_url="https://openrouter.ai/api/v1",
        openrouter_image_model="google/gemini-3.1-flash-image-preview",
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCreateProvider:

    def test_default_creates_dashscope(self) -> None:
        settings = _make_settings()  # image_gen_provider defaults to "dashscope"
        provider = create_provider(settings)
        assert isinstance(provider, DashScopeProvider)

    def test_explicit_dashscope(self) -> None:
        settings = _make_settings(image_gen_provider="dashscope")
        provider = create_provider(settings)
        assert isinstance(provider, DashScopeProvider)

    def test_openrouter(self) -> None:
        settings = _make_settings(image_gen_provider="openrouter")
        provider = create_provider(settings)
        assert isinstance(provider, OpenRouterProvider)

    def test_invalid_raises(self) -> None:
        settings = _make_settings(image_gen_provider="invalid_provider")
        with pytest.raises(ValueError, match="invalid_provider"):
            create_provider(settings)

    def test_case_insensitive(self) -> None:
        settings = _make_settings(image_gen_provider="OpenRouter")
        provider = create_provider(settings)
        assert isinstance(provider, OpenRouterProvider)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_factory.py -v`
Expected: FAIL — `ModuleNotFoundError` / missing config fields

- [ ] **Step 3: Add config fields**

Modify `backend/app/config.py` — add after existing `qwen_image_max_retries` line:

```python
    # Image generation provider switch
    image_gen_provider: str = "dashscope"  # "dashscope" | "openrouter"

    # OpenRouter image generation
    openrouter_image_apikey: str = ""
    openrouter_image_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_image_model: str = "google/gemini-2.5-flash-image"
    openrouter_image_timeout: int = 120
    openrouter_image_max_retries: int = 3
```

- [ ] **Step 4: Implement factory.py**

Create `backend/app/services/image_gen/factory.py`:

```python
"""Factory for creating image generation providers based on config."""

from __future__ import annotations

from app.config import Settings
from app.services.image_gen.dashscope_provider import DashScopeProvider
from app.services.image_gen.openrouter_provider import OpenRouterProvider


def create_provider(settings: Settings) -> DashScopeProvider | OpenRouterProvider:
    """根据 settings.image_gen_provider 创建对应的 provider 实例。"""
    name = settings.image_gen_provider.lower().strip()

    if name == "dashscope":
        return DashScopeProvider(
            api_key=settings.qwen_image_apikey,
            base_url=settings.qwen_image_base_url,
            model=settings.qwen_image_model,
            timeout=float(settings.qwen_image_timeout),
            max_retries=settings.qwen_image_max_retries,
        )

    if name == "openrouter":
        return OpenRouterProvider(
            api_key=settings.openrouter_image_apikey,
            base_url=settings.openrouter_image_base_url,
            model=settings.openrouter_image_model,
            timeout=float(settings.openrouter_image_timeout),
            max_retries=settings.openrouter_image_max_retries,
        )

    raise ValueError(
        f"Unknown image_gen_provider: '{settings.image_gen_provider}'. "
        f"Supported: 'dashscope', 'openrouter'"
    )
```

- [ ] **Step 5: Update __init__.py with public API**

Update `backend/app/services/image_gen/__init__.py`:

```python
"""Image generation multi-provider module.

Public API:
    create_image_gen_client() — factory function
    ImageGenApiError, ImageGenTimeoutError — exception types
    ImageSize — size value type
    ImageGenProvider — protocol for type hints
"""

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageGenProvider,
    ImageSize,
)
from app.services.image_gen.factory import create_provider as create_image_gen_client

__all__ = [
    "create_image_gen_client",
    "ImageGenApiError",
    "ImageGenTimeoutError",
    "ImageGenProvider",
    "ImageSize",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_factory.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/image_gen/factory.py backend/app/services/image_gen/__init__.py backend/app/config.py tests/backend/unit/test_image_gen_factory.py
git commit -m "feat(image-gen): add factory + config for provider switching"
```

---

### Task 5: Rewrite image_gen_client.py as backward-compatible wrapper

**Files:**
- Modify: `backend/app/services/image_gen_client.py`
- Modify: `tests/backend/unit/test_image_gen_client.py`

- [ ] **Step 1: Run existing tests to confirm green baseline**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_client.py -v`
Expected: All existing tests PASS (green baseline)

- [ ] **Step 2: Rewrite image_gen_client.py as thin wrapper**

Replace entire content of `backend/app/services/image_gen_client.py`:

```python
"""Backward-compatible image generation client.

Delegates to the provider selected by settings.image_gen_provider.
Preserves the original ImageGenClient interface and import paths so that
comic_node.py, routers/comic.py, and all existing tests continue to work.
"""

from __future__ import annotations

import logging

from langsmith import traceable

from app.config import Settings
from app.services.image_gen import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    create_image_gen_client,
)

logger = logging.getLogger(__name__)

# Re-export exceptions so existing `from app.services.image_gen_client import ...` works
__all__ = ["ImageGenClient", "ImageGenApiError", "ImageGenTimeoutError"]


class ImageGenClient:
    """向后兼容包装 — 委托给 provider 实现。

    保持与旧版完全相同的方法签名：
        generate_from_text(prompt, size="1536*2688") -> str
        generate(prompt, image_base64, image_format="jpeg", size="1024*1024") -> str
    """

    def __init__(self, settings: Settings) -> None:
        self._provider = create_image_gen_client(settings)
        self._provider_name = settings.image_gen_provider

    @traceable(run_type="tool", name="image_gen")
    async def generate_from_text(
        self,
        prompt: str,
        size: str = "1536*2688",
    ) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        image_size = self._parse_size(size)
        logger.info("ImageGenClient.generate_from_text (provider=%s)", self._provider_name)
        return await self._provider.generate_from_text(prompt, image_size)

    async def generate(
        self,
        prompt: str,
        image_base64: str,
        image_format: str = "jpeg",
        size: str = "1024*1024",
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 字符串。"""
        image_size = self._parse_size(size)
        logger.info("ImageGenClient.generate (provider=%s)", self._provider_name)
        return await self._provider.generate(prompt, image_base64, image_size)

    @staticmethod
    def _parse_size(size: str) -> ImageSize:
        """Parse 'W*H' string into ImageSize."""
        parts = size.split("*")
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: '{size}', expected 'W*H'")
        return ImageSize(int(parts[0]), int(parts[1]))
```

- [ ] **Step 3: Run existing tests — expect failures due to test internals**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_client.py -v`
Expected: Some tests FAIL because they mock `httpx.AsyncClient` directly, but the wrapper now delegates. Tests that check DashScope-specific payload structure need updating.

- [ ] **Step 4: Update test_image_gen_client.py**

Replace entire content of `tests/backend/unit/test_image_gen_client.py`:

```python
"""ImageGenClient backward-compatibility tests.

Verifies the thin wrapper delegates correctly and preserves the old interface.
DashScope-specific behavior is tested in test_dashscope_provider.py.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.services.image_gen_client import (
    ImageGenClient,
    ImageGenApiError,
    ImageGenTimeoutError,
)
from app.services.image_gen.base import ImageSize


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
        image_gen_provider="dashscope",
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


# ---------------------------------------------------------------------------
# Import compatibility
# ---------------------------------------------------------------------------

class TestImportCompat:
    """Verify old import paths still work."""

    def test_exceptions_importable(self) -> None:
        from app.services.image_gen_client import ImageGenApiError as E1
        from app.services.image_gen_client import ImageGenTimeoutError as E2
        assert E1 is not None
        assert E2 is not None

    def test_client_importable(self) -> None:
        from app.services.image_gen_client import ImageGenClient as C
        assert C is not None


# ---------------------------------------------------------------------------
# Size parsing
# ---------------------------------------------------------------------------

class TestSizeParsing:

    def test_standard(self) -> None:
        result = ImageGenClient._parse_size("1536*2688")
        assert result == ImageSize(1536, 2688)

    def test_square(self) -> None:
        result = ImageGenClient._parse_size("1024*1024")
        assert result == ImageSize(1024, 1024)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid size"):
            ImageGenClient._parse_size("bad-format")


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

class TestDelegation:

    @pytest.mark.asyncio
    async def test_generate_from_text_delegates(self) -> None:
        """Wrapper delegates to provider.generate_from_text."""
        settings = _make_settings()
        client = ImageGenClient(settings)

        mock_result = "data:image/png;base64,abc123"
        client._provider = AsyncMock()
        client._provider.generate_from_text = AsyncMock(return_value=mock_result)

        result = await client.generate_from_text("draw a cat", size="1536*2688")

        assert result == mock_result
        client._provider.generate_from_text.assert_awaited_once_with(
            "draw a cat", ImageSize(1536, 2688)
        )

    @pytest.mark.asyncio
    async def test_generate_delegates(self) -> None:
        """Wrapper delegates to provider.generate."""
        settings = _make_settings()
        client = ImageGenClient(settings)

        mock_result = "data:image/png;base64,xyz789"
        client._provider = AsyncMock()
        client._provider.generate = AsyncMock(return_value=mock_result)

        result = await client.generate("edit this", "base64data", size="1024*1024")

        assert result == mock_result
        client._provider.generate.assert_awaited_once_with(
            "edit this", "base64data", ImageSize(1024, 1024)
        )

    @pytest.mark.asyncio
    async def test_default_size_generate_from_text(self) -> None:
        """Default size for generate_from_text is 1536*2688."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        client._provider = AsyncMock()
        client._provider.generate_from_text = AsyncMock(return_value="data:image/png;base64,x")

        await client.generate_from_text("prompt")

        client._provider.generate_from_text.assert_awaited_once_with(
            "prompt", ImageSize(1536, 2688)
        )

    @pytest.mark.asyncio
    async def test_default_size_generate(self) -> None:
        """Default size for generate is 1024*1024."""
        settings = _make_settings()
        client = ImageGenClient(settings)
        client._provider = AsyncMock()
        client._provider.generate = AsyncMock(return_value="data:image/png;base64,x")

        await client.generate("prompt", "b64")

        client._provider.generate.assert_awaited_once_with(
            "prompt", "b64", ImageSize(1024, 1024)
        )


# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

class TestProviderSelection:

    def test_dashscope_by_default(self) -> None:
        from app.services.image_gen.dashscope_provider import DashScopeProvider
        settings = _make_settings()
        client = ImageGenClient(settings)
        assert isinstance(client._provider, DashScopeProvider)

    def test_openrouter_when_configured(self) -> None:
        from app.services.image_gen.openrouter_provider import OpenRouterProvider
        settings = _make_settings(
            image_gen_provider="openrouter",
            openrouter_image_apikey="sk-or-test",
        )
        client = ImageGenClient(settings)
        assert isinstance(client._provider, OpenRouterProvider)
```

- [ ] **Step 5: Run updated tests**

Run: `cd backend && uv run pytest tests/backend/unit/test_image_gen_client.py -v`
Expected: All 10 tests PASS

- [ ] **Step 6: Run full regression**

Run: `cd backend && uv run pytest tests/backend/unit/ -v`
Expected: ALL existing tests still PASS (including test_comic_node.py, test_comic_route.py etc.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/image_gen_client.py tests/backend/unit/test_image_gen_client.py
git commit -m "refactor(image-gen): rewrite client as backward-compatible wrapper"
```

---

### Task 6: Update .env files and config documentation

**Files:**
- Modify: `.env.example`
- Modify: `backend/.env.example`

- [ ] **Step 1: Update root .env.example**

Add after existing Qwen section:

```env
# Image generation provider: "dashscope" or "openrouter"
IMAGE_GEN_PROVIDER=dashscope

# OpenRouter image generation (when IMAGE_GEN_PROVIDER=openrouter)
OPENROUTER_IMAGE_APIKEY=your-openrouter-api-key
OPENROUTER_IMAGE_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image
```

- [ ] **Step 2: Update backend .env.example**

Add same section after existing Qwen section:

```env
# ===== Image generation provider =====
IMAGE_GEN_PROVIDER=dashscope

# ===== OpenRouter image generation =====
OPENROUTER_IMAGE_APIKEY=your-openrouter-api-key
OPENROUTER_IMAGE_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image
```

- [ ] **Step 3: Commit**

```bash
git add .env.example backend/.env.example
git commit -m "docs: add OpenRouter config to .env.example files"
```

---

### Task 7: Real API integration tests

**Files:**
- Modify: `tests/backend/integration/test_real_api.py`

- [ ] **Step 1: Add OpenRouter integration tests**

Add to `tests/backend/integration/test_real_api.py`, after existing imports add:

```python
from app.services.image_gen.openrouter_provider import OpenRouterProvider
from app.services.image_gen.base import ImageSize
```

Add helper function:

```python
def _has_openrouter_key() -> bool:
    """Check if OpenRouter API key is configured."""
    try:
        s = Settings()
        return bool(s.openrouter_image_apikey)
    except Exception:
        return False


skip_no_openrouter = pytest.mark.skipif(
    not _has_openrouter_key(),
    reason="OpenRouter API key not configured in .env",
)
```

Add test class before the `TestFullE2EFlow` class:

```python
# ── Stage 2b: OpenRouter — real image generation ────────────────────────


@skip_no_openrouter
@pytest.mark.asyncio
class TestOpenRouterImageGen:
    """OpenRouter: real Gemini image generation call."""

    async def test_generate_from_text_returns_base64(self, real_settings):
        """OpenRouterProvider returns valid base64 PNG."""
        provider = OpenRouterProvider(
            api_key=real_settings.openrouter_image_apikey,
            base_url=real_settings.openrouter_image_base_url,
            model=real_settings.openrouter_image_model,
            timeout=float(real_settings.openrouter_image_timeout),
            max_retries=real_settings.openrouter_image_max_retries,
        )

        result = await provider.generate_from_text(
            prompt="A simple 4-panel comic strip about a cat learning to code. "
                   "Clean line art, speech bubbles, warm colors.",
            size=ImageSize(768, 1344),  # 9:16 but smaller for speed
        )

        assert result.startswith("data:image/")
        assert ";base64," in result

    async def test_image_is_decodable(self, real_settings):
        """Generated image can be decoded to valid PNG."""
        provider = OpenRouterProvider(
            api_key=real_settings.openrouter_image_apikey,
            base_url=real_settings.openrouter_image_base_url,
            model=real_settings.openrouter_image_model,
            timeout=float(real_settings.openrouter_image_timeout),
            max_retries=real_settings.openrouter_image_max_retries,
        )

        result = await provider.generate_from_text(
            prompt="A blue square with the text 'TEST' in white.",
            size=ImageSize(1024, 1024),
        )

        # Decode base64
        b64_part = result.split(",", 1)[1]
        image_bytes = base64.b64decode(b64_part)
        assert len(image_bytes) > 100  # Not empty

        img = Image.open(BytesIO(image_bytes))
        assert img.size[0] > 0 and img.size[1] > 0


@skip_no_openrouter
@pytest.mark.asyncio
class TestComicGraphOpenRouter:
    """ComicGraph with OpenRouter provider — full pipeline."""

    async def test_comic_full_pipeline_openrouter(self, real_settings):
        """Full comic generation using OpenRouter instead of DashScope."""
        import os
        os.environ["IMAGE_GEN_PROVIDER"] = "openrouter"
        from app.dependencies import get_cached_settings
        get_cached_settings.cache_clear()

        # Reload settings with openrouter
        or_settings = Settings()

        from app.graphs.comic_graph import build_comic_graph
        graph = build_comic_graph()
        inputs = {
            "slang": "Piece of cake",
            "origin": "English idiom",
            "explanation": "Something very easy to do",
            "panel_count": 8,
            "panels": [
                {"scene": f"Simple scene {i+1} with a character", "dialogue": ""}
                for i in range(8)
            ],
        }

        result = await graph.ainvoke(
            inputs,
            config={"configurable": {"settings": or_settings}},
        )

        assert result["comic_url"].startswith("/data/comics/")
        assert result["history_id"]

        # Cleanup
        os.environ["IMAGE_GEN_PROVIDER"] = "dashscope"
        get_cached_settings.cache_clear()
```

- [ ] **Step 2: Also update the `real_settings` fixture to include OpenRouter fields**

In the `real_settings` fixture, the Settings() call already reads from `.env`, so if `.env` has the OpenRouter keys, they'll be loaded automatically. No fixture change needed.

- [ ] **Step 3: Run OpenRouter integration tests only**

Run: `cd backend && uv run pytest tests/backend/integration/test_real_api.py::TestOpenRouterImageGen -v -s`
Expected: 2 tests PASS (or SKIP if no key configured)

- [ ] **Step 4: Run full integration suite to verify DashScope still works**

Run: `cd backend && uv run pytest tests/backend/integration/test_real_api.py -v -s`
Expected: All existing DashScope tests still PASS, OpenRouter tests PASS (or SKIP)

- [ ] **Step 5: Commit**

```bash
git add tests/backend/integration/test_real_api.py
git commit -m "test: add OpenRouter real API integration tests"
```

---

### Task 8: Standalone verification script + cleanup

**Files:**
- Create: `scripts/verify_providers.py` (temporary — delete after verification)

- [ ] **Step 1: Create verification script**

Create `scripts/verify_providers.py`:

```python
"""Standalone verification: test both image gen providers with real APIs.

Usage:
    uv run python scripts/verify_providers.py

Requires .env with both DashScope and OpenRouter keys configured.
Delete this script after successful verification.
"""

import asyncio
import base64
import sys
from io import BytesIO
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.config import Settings
from app.services.image_gen.base import ImageSize
from app.services.image_gen.dashscope_provider import DashScopeProvider
from app.services.image_gen.openrouter_provider import OpenRouterProvider


PROMPT = (
    "A 4-panel manga comic strip about a robot learning to paint. "
    "Clean line art, speech bubbles, warm colors, white panel borders."
)
SIZE_COMIC = ImageSize(768, 1344)  # 9:16, smaller for speed
SIZE_SQUARE = ImageSize(1024, 1024)


def _validate_base64_image(result: str, label: str) -> None:
    """Validate result is a decodable image."""
    assert result.startswith("data:image/"), f"[{label}] Not a data URL: {result[:50]}"
    assert ";base64," in result, f"[{label}] No base64 marker"

    b64_part = result.split(",", 1)[1]
    image_bytes = base64.b64decode(b64_part)
    assert len(image_bytes) > 100, f"[{label}] Image too small: {len(image_bytes)} bytes"

    from PIL import Image
    img = Image.open(BytesIO(image_bytes))
    w, h = img.size
    assert w > 0 and h > 0, f"[{label}] Invalid dimensions: {w}x{h}"
    print(f"  [OK] {label}: {w}x{h}, {len(image_bytes):,} bytes")


async def test_dashscope(settings: Settings) -> bool:
    """Test DashScope provider."""
    print("\n=== DashScope (Qwen Image 2.0) ===")
    if not settings.qwen_image_apikey:
        print("  [SKIP] qwen_image_apikey not set")
        return False

    provider = DashScopeProvider(
        api_key=settings.qwen_image_apikey,
        base_url=settings.qwen_image_base_url,
        model=settings.qwen_image_model,
        timeout=float(settings.qwen_image_timeout),
        max_retries=settings.qwen_image_max_retries,
    )

    try:
        result = await provider.generate_from_text(PROMPT, SIZE_COMIC)
        _validate_base64_image(result, "DashScope text-to-image")
        return True
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False


async def test_openrouter(settings: Settings) -> bool:
    """Test OpenRouter provider."""
    print("\n=== OpenRouter (Gemini Flash Image) ===")
    if not settings.openrouter_image_apikey:
        print("  [SKIP] openrouter_image_apikey not set")
        return False

    provider = OpenRouterProvider(
        api_key=settings.openrouter_image_apikey,
        base_url=settings.openrouter_image_base_url,
        model=settings.openrouter_image_model,
        timeout=float(settings.openrouter_image_timeout),
        max_retries=settings.openrouter_image_max_retries,
    )

    try:
        result = await provider.generate_from_text(PROMPT, SIZE_COMIC)
        _validate_base64_image(result, "OpenRouter text-to-image")
        return True
    except Exception as exc:
        print(f"  [FAIL] {type(exc).__name__}: {exc}")
        return False


async def test_wrapper(settings: Settings) -> bool:
    """Test ImageGenClient wrapper with both providers."""
    print("\n=== ImageGenClient wrapper ===")
    from app.services.image_gen_client import ImageGenClient

    success = True

    # Test with dashscope (if key available)
    if settings.qwen_image_apikey:
        import os
        os.environ["IMAGE_GEN_PROVIDER"] = "dashscope"
        from app.dependencies import get_cached_settings
        get_cached_settings.cache_clear()
        s = Settings()
        try:
            client = ImageGenClient(s)
            result = await client.generate_from_text(PROMPT, size="768*1344")
            _validate_base64_image(result, "Wrapper(dashscope)")
        except Exception as exc:
            print(f"  [FAIL] Wrapper(dashscope): {type(exc).__name__}: {exc}")
            success = False

    # Test with openrouter (if key available)
    if settings.openrouter_image_apikey:
        import os
        os.environ["IMAGE_GEN_PROVIDER"] = "openrouter"
        from app.dependencies import get_cached_settings
        get_cached_settings.cache_clear()
        s = Settings()
        try:
            client = ImageGenClient(s)
            result = await client.generate_from_text(PROMPT, size="768*1344")
            _validate_base64_image(result, "Wrapper(openrouter)")
        except Exception as exc:
            print(f"  [FAIL] Wrapper(openrouter): {type(exc).__name__}: {exc}")
            success = False

    return success


async def main() -> None:
    print("=" * 60)
    print("Image Generation Provider Verification")
    print("=" * 60)

    settings = Settings()
    results: dict[str, bool] = {}

    results["dashscope"] = await test_dashscope(settings)
    results["openrouter"] = await test_openrouter(settings)
    results["wrapper"] = await test_wrapper(settings)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else ("SKIP" if passed is False else "FAIL")
        print(f"  {name}: {status}")

    all_tested = [v for v in results.values() if v is not False]
    if all_tested and all(all_tested):
        print("\nAll configured providers verified successfully!")
        print("You can delete this script: rm scripts/verify_providers.py")
    else:
        print("\nSome tests failed. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Add OpenRouter credentials to .env**

Add to `.env`:
```env
IMAGE_GEN_PROVIDER=dashscope
OPENROUTER_IMAGE_APIKEY=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
OPENROUTER_IMAGE_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_IMAGE_MODEL=google/gemini-3.1-flash-image-preview
```

- [ ] **Step 3: Run verification**

Run: `uv run python scripts/verify_providers.py`
Expected: Both providers PASS, wrapper PASS

- [ ] **Step 4: Delete verification script after success**

```bash
rm scripts/verify_providers.py
```

- [ ] **Step 5: Final full regression**

Run: `cd backend && uv run pytest tests/backend/unit/ -v`
Expected: ALL unit tests PASS

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat(image-gen): complete multi-provider support (DashScope + OpenRouter)"
```
