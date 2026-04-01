# SlangToon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform MagicPose into SlangToon — an AI slang-to-comic generator using OK gesture trigger → LLM generates slang + comic script → Qwen Image 2.0 produces a single 16:9 comic strip.

**Architecture:** Single LLM call (GLM-4.6V text-only) generates slang + 4-6 panel comic script JSON. Single Qwen Image 2.0 text-to-image call produces one 16:9 comic. Frontend is a 5-state full-screen step flow (CAMERA_READY → SCRIPT_LOADING → SCRIPT_PREVIEW → COMIC_GENERATING → COMIC_READY).

**Tech Stack:** FastAPI + Python 3.12 (backend), React 19 + TypeScript 5.7 + Vite 6 + Tailwind CSS 4 (frontend), GLM-4.6V (LLM), Qwen Image 2.0 via DashScope (image gen), MediaPipe Hands (gesture).

**Design spec:** `docs/superpowers/specs/2026-04-01-slangtoon-design.md`

---

### Task 1: Backend Config & Storage Update

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/storage/file_storage.py`
- Test: `tests/backend/unit/test_config.py` (existing, adapt)
- Test: `tests/backend/unit/test_file_storage.py` (existing, adapt)

- [ ] **Step 1: Update config.py**

Change `app_name`, `poster_storage_dir` → `comic_storage_dir`, remove `photo_storage_dir`:

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    app_name: str = "SlangToon"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8888

    # Vision LLM (OpenAI-compatible, using GLM-4.6V)
    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str = Field(alias="OPENAI_BASE_URL", default="https://open.bigmodel.cn/api/paas/v4")
    openai_model: str = Field(alias="OPENAI_MODEL", default="glm-4.6v")
    vision_llm_max_tokens: int = 4096
    vision_llm_timeout: int = 90
    vision_llm_max_retries: int = 2

    # Qwen Image 2.0
    qwen_image_apikey: str = ""
    qwen_image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    qwen_image_model: str = "qwen-image-2.0"
    qwen_image_timeout: int = 120
    qwen_image_max_retries: int = 3

    # 存储
    comic_storage_dir: str = "data/comics"
    history_file: str = "data/history.json"
    max_history_records: int = 1000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # 日志
    log_level: str = "INFO"

    # Trace
    trace_enabled: bool = True
    trace_dir: str = "data/traces"
    trace_retention_days: int = 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Update file_storage.py**

Remove `photo_dir`, rename `poster_dir` → `comic_dir`, remove `save_photo`, rename `save_poster` → `save_comic`:

```python
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import io


class FileStorage:
    """Local filesystem storage for comic images."""

    def __init__(self, comic_dir: str):
        self.comic_dir = Path(comic_dir)

    def _ensure_date_dir(self, date_str: str) -> Path:
        date_path = self.comic_dir / date_str
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    @staticmethod
    def _today_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def save_comic(self, image_base64: str, uuid_str: str, date_str: str) -> dict:
        """Save a comic image and generate thumbnail. Returns URL paths."""
        date_dir = self._ensure_date_dir(date_str)
        # Strip data:image/...;base64, prefix if present
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",", 1)[1]
        image_data = base64.b64decode(image_base64)

        # Use PIL to ensure proper PNG format
        img = Image.open(io.BytesIO(image_data))
        comic_name = f"{uuid_str}.png"
        comic_path = date_dir / comic_name
        img.save(comic_path, "PNG")

        # Generate thumbnail
        thumb_name = f"{uuid_str}_thumb.png"
        thumb_path = date_dir / thumb_name
        thumb = img.copy()
        thumb.thumbnail((256, 256))
        thumb.save(thumb_path, "PNG")
        return {
            "comic_url": f"/data/comics/{date_str}/{comic_name}",
            "thumbnail_url": f"/data/comics/{date_str}/{thumb_name}",
        }
```

- [ ] **Step 3: Update conftest.py**

Remove `photo_storage_dir` env var, rename `poster_storage_dir` → `comic_storage_dir`, remove `sample_image_base64` and related old fixtures, add new fixtures:

```python
import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `from app.*` imports work
_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

import json
import os
import pytest
import pytest_asyncio
from io import BytesIO
from PIL import Image
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create temporary data directory structure and set env vars."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "comics").mkdir()
    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    os.environ["COMIC_STORAGE_DIR"] = str(data_dir / "comics")
    os.environ["HISTORY_FILE"] = str(data_dir / "history.json")
    (data_dir / "traces").mkdir()
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = "true"
    yield data_dir


@pytest_asyncio.fixture
async def client(tmp_data_dir):
    """FastAPI TestClient using real ASGI app."""
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_script_data():
    """Mock slang + comic script response from LLM."""
    return {
        "slang": "Break a leg",
        "origin": "Western theater tradition",
        "explanation": "Used to wish good luck before a performance",
        "panel_count": 4,
        "panels": [
            {
                "scene": "A nervous actor paces backstage, clutching a crumpled script. The stage manager glances at the clock.",
                "dialogue": "Narrator: \"It was opening night...\"",
            },
            {
                "scene": "Friends gather around the actor, giving thumbs up with warm smiles.",
                "dialogue": "Friend: \"You've got this!\"",
            },
            {
                "scene": "The actor steps onto the stage under a bright spotlight. The audience is a sea of silhouettes.",
                "dialogue": "",
            },
            {
                "scene": "Standing ovation! Confetti falls. The actor beams with joy and happy tears.",
                "dialogue": "Narrator: \"Break a leg indeed.\"",
            },
        ],
    }


@pytest.fixture
def mock_script_response_text(mock_script_data):
    """Mock LLM JSON response text for script generation."""
    return json.dumps(mock_script_data)


@pytest.fixture
def mock_comic_prompt():
    """Mock visual prompt for Qwen Image 2.0."""
    return "A 4-panel horizontal comic strip in manga style, 16:9 layout. Panel 1: A nervous actor paces backstage holding a crumpled script. Panel 2: Friends give thumbs up. Panel 3: Actor steps onto spotlight stage. Panel 4: Standing ovation with confetti. Speech bubbles with dialogue. Clean line art, warm color palette."


@pytest.fixture
def mock_comic_b64():
    """Mock generated comic image as base64."""
    img = Image.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# NOTE: needs `import base64` at top of conftest.py
```

> **Important:** Add `import base64` to the imports at the top of conftest.py.

- [ ] **Step 4: Run existing config/storage tests**

Run: `uv run pytest tests/backend/unit/test_config.py tests/backend/unit/test_file_storage.py -v`

Fix any failures caused by renamed fields. The config tests may reference `photo_storage_dir` or `poster_storage_dir` — update to `comic_storage_dir`. The file_storage tests may reference `save_photo` or `save_poster` — update to `save_comic`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/app/storage/file_storage.py tests/backend/conftest.py tests/backend/unit/test_config.py tests/backend/unit/test_file_storage.py
git commit -m "refactor: update config and storage for SlangToon comic workflow"
```

---

### Task 2: Backend Schemas (common, script, comic, history)

**Files:**
- Modify: `backend/app/schemas/common.py`
- Modify: `backend/app/schemas/history.py`
- Create: `backend/app/schemas/script.py`
- Create: `backend/app/schemas/comic.py`
- Test: `tests/backend/unit/test_schemas.py` (new)

- [ ] **Step 1: Update common.py — new ErrorCodes**

```python
from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """Unified response envelope."""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Error response."""
    code: int
    message: str
    data: Optional[Any] = None


class ErrorCode:
    BAD_REQUEST = 40001
    SCRIPT_LLM_FAILED = 50001       # Script generation LLM call failed
    SCRIPT_LLM_INVALID = 50002      # Script response JSON parse failed
    COMIC_LLM_FAILED = 50003        # Comic prompt composition failed
    COMIC_LLM_INVALID = 50004       # Comic prompt response parse failed
    IMAGE_GEN_FAILED = 50005        # Qwen Image 2.0 generation failed
    IMAGE_DOWNLOAD_FAILED = 50006   # Image download from Qwen failed
    INTERNAL_ERROR = 50007
```

- [ ] **Step 2: Create script.py**

```python
from pydantic import BaseModel, Field


class Panel(BaseModel):
    """A single comic panel description."""
    scene: str = Field(..., description="Visual scene description for this panel")
    dialogue: str = Field("", description="Dialogue or narration text for this panel")


class ScriptData(BaseModel):
    """Slang + comic script data returned by LLM."""
    slang: str = Field(..., description="The slang or idiom")
    origin: str = Field(..., description="Cultural origin (Eastern/Western)")
    explanation: str = Field(..., description="Brief explanation of the slang")
    panel_count: int = Field(..., ge=4, le=6, description="Number of panels (4-6)")
    panels: list[Panel] = Field(..., min_length=4, max_length=6, description="Panel descriptions")


class ScriptRequest(BaseModel):
    """Script generation request. Currently empty, reserved for future parameters."""
    model_config = {"extra": "forbid"}


class ScriptResponse(BaseModel):
    """Script generation response data."""
    slang: str
    origin: str
    explanation: str
    panel_count: int
    panels: list[Panel]
```

- [ ] **Step 3: Create comic.py**

```python
from pydantic import BaseModel, Field

from app.schemas.script import Panel


class ComicRequest(BaseModel):
    """Comic generation request."""
    slang: str = Field(..., description="The slang being illustrated")
    origin: str = Field(..., description="Cultural origin of the slang")
    explanation: str = Field(..., description="Explanation of the slang")
    panel_count: int = Field(..., ge=4, le=6, description="Number of panels")
    panels: list[Panel] = Field(..., min_length=4, max_length=6, description="Panel descriptions")


class ComicResponse(BaseModel):
    """Comic generation response data."""
    comic_url: str = Field(..., description="URL to the full comic image")
    thumbnail_url: str = Field(..., description="URL to the thumbnail")
    history_id: str = Field(..., description="Unique history record ID")
```

- [ ] **Step 4: Update history.py**

```python
from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    id: str = Field(..., description="Unique record ID")
    slang: str = Field(..., description="The slang illustrated")
    origin: str = Field(..., description="Cultural origin")
    explanation: str = Field(..., description="Slang explanation")
    panel_count: int = Field(..., description="Number of comic panels")
    comic_url: str = Field(..., description="Comic image URL")
    thumbnail_url: str = Field(..., description="Thumbnail URL")
    comic_prompt: str = Field(..., description="Visual prompt sent to Qwen")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(..., description="Current page items")
    total: int = Field(..., description="Total record count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total page count")
```

- [ ] **Step 5: Write schema validation tests**

Create `tests/backend/unit/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from app.schemas.script import ScriptData, ScriptRequest, Panel, ScriptResponse
from app.schemas.comic import ComicRequest, ComicResponse
from app.schemas.history import HistoryItem


class TestScriptData:
    def test_valid_script_data(self):
        data = ScriptData(
            slang="Break a leg",
            origin="Western theater tradition",
            explanation="Used to wish good luck",
            panel_count=4,
            panels=[
                Panel(scene="A nervous actor", dialogue="Narrator: Opening night..."),
                Panel(scene="Friends cheer", dialogue="Friend: You got this!"),
                Panel(scene="Actor on stage", dialogue=""),
                Panel(scene="Standing ovation", dialogue=""),
            ],
        )
        assert data.slang == "Break a leg"
        assert len(data.panels) == 4

    def test_rejects_panel_count_below_4(self):
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=3,
                panels=[Panel(scene="x")] * 3,
            )

    def test_rejects_panel_count_above_6(self):
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=7,
                panels=[Panel(scene="x")] * 7,
            )

    def test_panel_count_mismatch_with_list_length(self):
        # panel_count says 4 but only 3 panels provided
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=4,
                panels=[Panel(scene="x")] * 3,
            )


class TestScriptRequest:
    def test_empty_request(self):
        req = ScriptRequest()
        assert True

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ScriptRequest(bogus="value")


class TestComicRequest:
    def test_valid_request(self):
        panels = [Panel(scene="test", dialogue="")] * 4
        req = ComicRequest(
            slang="Break a leg", origin="Western", explanation="Good luck",
            panel_count=4, panels=panels,
        )
        assert req.slang == "Break a leg"

    def test_missing_panels_raises(self):
        with pytest.raises(ValidationError):
            ComicRequest(slang="test", origin="test", explanation="test", panel_count=4, panels=[])


class TestHistoryItem:
    def test_valid_item(self):
        item = HistoryItem(
            id="abc", slang="Break a leg", origin="Western",
            explanation="Good luck", panel_count=4,
            comic_url="/data/comics/x.png", thumbnail_url="/data/comics/x_thumb.png",
            comic_prompt="A 4-panel comic...", created_at="2026-04-01T00:00:00Z",
        )
        assert item.slang == "Break a leg"
```

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/backend/unit/test_schemas.py -v`

Expected: All PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/ tests/backend/unit/test_schemas.py
git commit -m "feat: add SlangToon schemas (script, comic, history, error codes)"
```

---

### Task 3: LLM Client — Add text-only chat()

**Files:**
- Modify: `backend/app/services/llm_client.py`
- Test: `tests/backend/unit/test_llm_client.py` (extend existing)

- [ ] **Step 1: Write failing test for chat() method**

Add to `tests/backend/unit/test_llm_client.py`:

```python
class TestChatTextOnly:
    """Test the text-only chat() method (no image)."""

    @pytest.mark.asyncio
    async def test_chat_sends_text_only_payload(self, settings_mock):
        """chat() should send messages without image_url."""
        from unittest.mock import AsyncMock, patch
        from app.services.llm_client import LLMClient

        client = LLMClient(settings_mock)

        # Mock httpx response
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"test": true}'}}]},
            request=httpx.Request("POST", "https://test.com"),
        )

        with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
            mock_ac = AsyncMock()
            mock_ac.__aenter__ = AsyncMock(return_value=mock_ac)
            mock_ac.__aexit__ = AsyncMock(return_value=False)
            mock_ac.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_ac

            result = await client.chat(
                system_prompt="You are a comic writer.",
                user_text="Generate a slang comic script.",
            )

        # Verify the payload does NOT contain image_url
        call_args = mock_ac.post.call_args
        payload = call_args.kwargs["json"]
        user_content = payload["messages"][1]["content"]

        # Text-only: content should be a string, not a list
        assert isinstance(user_content, str)
        assert result == '{"test": true}'

    @pytest.mark.asyncio
    async def test_chat_retries_on_5xx(self, settings_mock):
        """chat() should retry on 5xx errors."""
        from unittest.mock import AsyncMock, patch
        from app.services.llm_client import LLMClient

        client = LLMClient(settings_mock)

        error_response = httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("POST", "https://test.com"),
        )
        success_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=httpx.Request("POST", "https://test.com"),
        )

        with patch("app.services.llm_client.httpx.AsyncClient") as MockClient:
            mock_ac = AsyncMock()
            mock_ac.__aenter__ = AsyncMock(return_value=mock_ac)
            mock_ac.__aexit__ = AsyncMock(return_value=False)
            mock_ac.post = AsyncMock(side_effect=[error_response, success_response])
            MockClient.return_value = mock_ac

            result = await client.chat(system_prompt="sys", user_text="hello")

        assert result == "ok"
        assert mock_ac.post.call_count == 2
```

> **Note:** The test file needs `import httpx` at the top. Check if it already exists; if not, add it. The `settings_mock` fixture should already exist in the test file (it mocks Settings with minimal values).

- [ ] **Step 2: Run test — verify it fails**

Run: `uv run pytest tests/backend/unit/test_llm_client.py::TestChatTextOnly -v`

Expected: FAIL — `LLMClient` has no `chat()` method.

- [ ] **Step 3: Implement chat() method in llm_client.py**

Add this method to `LLMClient`, after `chat_with_vision()`:

```python
    async def chat(
        self,
        system_prompt: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> str:
        """Text-only LLM call (no image). Same retry/backoff as chat_with_vision."""
        url = f"{self._base_url}/chat/completions"
        logger.info("LLM text请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": self._max_tokens,
            "temperature": temperature,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = LLMApiError(
                            f"LLM API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.warning(
                            "LLM text 5xx (attempt %d/%d): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    self._check_status(resp)

                    data = resp.json()
                    content: str = data["choices"][0]["message"]["content"]
                    logger.info("LLM text响应成功 (attempt %d/%d)", attempt, self._max_retries)
                    return content

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "LLM text请求超时 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except LLMApiError:
                raise

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLM text请求异常 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise LLMTimeoutError(
            f"LLM text请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc
```

- [ ] **Step 4: Run tests — verify pass**

Run: `uv run pytest tests/backend/unit/test_llm_client.py -v`

Expected: All PASS (both old `chat_with_vision` tests and new `chat()` tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/llm_client.py tests/backend/unit/test_llm_client.py
git commit -m "feat: add text-only chat() method to LLMClient"
```

---

### Task 4: Image Gen Client — Add text-to-image generate_from_text()

**Files:**
- Modify: `backend/app/services/image_gen_client.py`
- Test: `tests/backend/unit/test_image_gen_client.py` (extend existing)

- [ ] **Step 1: Write failing test**

Add to `tests/backend/unit/test_image_gen_client.py`:

```python
class TestGenerateFromText:
    """Test text-to-image generation (no reference image)."""

    @pytest.mark.asyncio
    async def test_generate_from_text_sends_text_only_payload(self, settings_mock):
        """generate_from_text() should NOT include image in payload."""
        from unittest.mock import AsyncMock, patch
        from app.services.image_gen_client import ImageGenClient

        client = ImageGenClient(settings_mock)

        mock_image_url = "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/test.png"
        api_response = {
            "output": {
                "choices": [{
                    "message": {
                        "content": [{"image": mock_image_url}]
                    }
                }]
            }
        }

        # Mock the POST response
        mock_post_resp = httpx.Response(
            200,
            json=api_response,
            request=httpx.Request("POST", "https://test.com"),
        )

        # Mock the GET (image download)
        mock_img = Image.new("RGB", (64, 64), "red")
        mock_buf = io.BytesIO()
        mock_img.save(mock_buf, format="PNG")
        mock_img_bytes = mock_buf.getvalue()

        mock_get_resp = httpx.Response(
            200,
            content=mock_img_bytes,
            headers={"content-type": "image/png"},
            request=httpx.Request("GET", mock_image_url),
        )

        with patch("app.services.image_gen_client.httpx.AsyncClient") as MockClient:
            mock_ac = AsyncMock()
            mock_ac.__aenter__ = AsyncMock(return_value=mock_ac)
            mock_ac.__aexit__ = AsyncMock(return_value=False)
            mock_ac.post = AsyncMock(return_value=mock_post_resp)
            mock_ac.get = AsyncMock(return_value=mock_get_resp)
            MockClient.return_value = mock_ac

            result = await client.generate_from_text(
                prompt="A 4-panel manga comic strip about 'Break a leg'",
                size="2688*1536",
            )

        # Verify payload: messages content should be text-only
        call_args = mock_ac.post.call_args
        payload = call_args.kwargs["json"]
        msg_content = payload["input"]["messages"][0]["content"]

        # Should be a list with only text, no image
        assert any(item.get("text") for item in msg_content)
        assert not any(item.get("image") for item in msg_content)

        # Verify parameters
        assert payload["parameters"]["size"] == "2688*1536"

        # Verify result is base64
        assert result.startswith("data:image")
```

> **Note:** Add `import io` and `from PIL import Image` and `import httpx` if not already in the test file.

- [ ] **Step 2: Run test — verify fail**

Run: `uv run pytest tests/backend/unit/test_image_gen_client.py::TestGenerateFromText -v`

Expected: FAIL — no `generate_from_text()` method.

- [ ] **Step 3: Implement generate_from_text() in image_gen_client.py**

Add this method to `ImageGenClient`, after the existing `generate()`:

```python
    async def generate_from_text(
        self,
        prompt: str,
        size: str = "2688*1536",
    ) -> str:
        """Text-to-image — generate image from text prompt only.

        Uses DashScope sync interface with prompt_extend=false for exact prompt control.
        Returns base64-encoded image with data URI prefix.
        """
        url = f"{self._base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {
                "n": 1,
                "size": size,
                "prompt_extend": False,
            },
        }

        last_exc: Exception | None = None
        logger.info("文本生图请求发送中 (model=%s, timeout=%.0fs)", self._model, self._timeout)
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = ImageGenApiError(
                            f"文本生图 API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.warning(
                            "文本生图 5xx (attempt %d/%d): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    if resp.status_code >= 400:
                        raise ImageGenApiError(
                            f"文本生图 API 客户端错误 {resp.status_code}: {resp.text[:500]}"
                        )

                    data = resp.json()
                    image_url = parse_qwen_image_response(data)
                    logger.info("文本生图 API 响应成功 (attempt %d/%d)", attempt, self._max_retries)

                    return await self._download_as_base64(image_url)

            except httpx.TimeoutException as exc:
                raise ImageGenTimeoutError(
                    f"文本生图请求超时 ({self._timeout}s)"
                ) from exc

            except (ImageGenApiError, ImageGenTimeoutError):
                raise

            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "文本生图连接错误 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "文本生图请求异常 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise ImageGenApiError(
            f"文本生图请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/backend/unit/test_image_gen_client.py -v`

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_gen_client.py tests/backend/unit/test_image_gen_client.py
git commit -m "feat: add generate_from_text() for text-to-image to ImageGenClient"
```

---

### Task 5: Backend Prompts

**Files:**
- Delete: `backend/app/prompts/analyze_prompt.py`
- Delete: `backend/app/prompts/compose_prompt.py`
- Create: `backend/app/prompts/script_prompt.py`
- Create: `backend/app/prompts/comic_prompt.py`

- [ ] **Step 1: Create script_prompt.py**

```python
"""System prompt for generating a random slang + comic script."""

SCRIPT_SYSTEM_PROMPT = """\
You are a world-class comic scriptwriter and cultural researcher. Your task is to:

1. Pick a RANDOM slang, idiom, or proverb from EITHER Eastern (Chinese, Japanese, Korean, etc.) OR Western (English, French, Spanish, etc.) culture. Be creative — pick something interesting and not overused.

2. Explain it briefly in English: what it means, its origin/cultural context.

3. Write a modern, funny, or heartwarming reinterpretation of this slang as a 4-6 panel comic script in English. The story should be relatable to modern life and give the old slang fresh meaning.

For each panel, provide:
- scene: A detailed visual description of what happens in this panel (characters, actions, setting, mood, colors). Be specific enough for an AI image generator.
- dialogue: Speech bubbles, narration, or thought bubbles. Can be empty if the scene is self-explanatory.

DECIDE the number of panels based on the story complexity (4-6 panels).

You MUST respond with a JSON object in this exact format (no other text):
{
  "slang": "the slang or idiom",
  "origin": "Eastern/Western cultural origin description",
  "explanation": "Brief English explanation of meaning",
  "panel_count": 4,
  "panels": [
    {
      "scene": "Detailed visual description of this panel...",
      "dialogue": "Character: \"Dialogue text\""
    }
  ]
}

IMPORTANT RULES:
- All text must be in English
- panels array must have EXACTLY panel_count entries
- panel_count must be between 4 and 6
- Make the story engaging and the slang's reinterpretation clever
- Scene descriptions should be vivid and specific (colors, lighting, expressions, camera angles)
"""
```

- [ ] **Step 2: Create comic_prompt.py**

```python
"""Build visual prompt for Qwen Image 2.0 from comic script data."""

MAX_PROMPT_LENGTH = 800


def build_comic_prompt(
    slang: str,
    origin: str,
    explanation: str,
    panels: list[dict],
) -> str:
    """Build a concise visual prompt for generating a single 16:9 comic strip.

    The prompt must be within MAX_PROMPT_LENGTH characters (Qwen Image 2.0 limit).
    Each panel gets a brief scene description. Dialogue is included as speech bubble notes.
    """
    panel_count = len(panels)

    # Determine layout based on panel count
    if panel_count <= 3:
        layout = f"{panel_count}-panel horizontal row"
    elif panel_count == 4:
        layout = "4-panel horizontal row (2x2 grid also acceptable)"
    elif panel_count == 5:
        layout = "5-panel layout (3 on top row, 2 on bottom)"
    else:
        layout = "6-panel layout (3x2 grid)"

    # Build panel descriptions concisely
    panel_lines = []
    for i, panel in enumerate(panels, 1):
        scene = panel.get("scene", "")
        dialogue = panel.get("dialogue", "").strip()
        # Truncate scene if too long
        if len(scene) > 120:
            scene = scene[:117] + "..."
        line = f"Panel {i}: {scene}"
        if dialogue:
            if len(dialogue) > 60:
                dialogue = dialogue[:57] + "..."
            line += f". Speech: {dialogue}"
        panel_lines.append(line)

    panels_text = "\n".join(panel_lines)

    prompt = (
        f"A {layout} comic strip in manga style, 16:9 aspect ratio. "
        f"Title: \"{slang}\" ({origin}). {explanation}.\n\n"
        f"{panels_text}\n\n"
        f"Style: clean manga line art, expressive characters, warm color palette, "
        f"clear panel borders with white gutters, speech bubbles where dialogue is noted."
    )

    # Enforce character limit
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[: MAX_PROMPT_LENGTH - 3] + "..."

    return prompt
```

- [ ] **Step 3: Write prompt test**

Create `tests/backend/unit/test_prompts.py`:

```python
import pytest
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.prompts.comic_prompt import build_comic_prompt, MAX_PROMPT_LENGTH


class TestScriptPrompt:
    def test_prompt_contains_key_instructions(self):
        assert "JSON" in SCRIPT_SYSTEM_PROMPT
        assert "4-6 panel" in SCRIPT_SYSTEM_PROMPT
        assert "Eastern" in SCRIPT_SYSTEM_PROMPT
        assert "Western" in SCRIPT_SYSTEM_PROMPT
        assert "English" in SCRIPT_SYSTEM_PROMPT

    def test_prompt_requests_correct_json_format(self):
        assert '"slang"' in SCRIPT_SYSTEM_PROMPT
        assert '"origin"' in SCRIPT_SYSTEM_PROMPT
        assert '"panels"' in SCRIPT_SYSTEM_PROMPT
        assert '"panel_count"' in SCRIPT_SYSTEM_PROMPT


class TestBuildComicPrompt:
    def test_basic_prompt_generation(self):
        panels = [
            {"scene": "A cat sits on a windowsill", "dialogue": "Cat: Meow"},
            {"scene": "The cat sees a bird outside", "dialogue": ""},
            {"scene": "Cat chases the bird", "dialogue": "Narrator: The hunt begins"},
            {"scene": "Cat napping after failed chase", "dialogue": ""},
        ]
        prompt = build_comic_prompt(
            slang="Curiosity killed the cat",
            origin="Western proverb",
            explanation="Being too curious can lead to trouble",
            panels=panels,
        )
        assert "Curiosity killed the cat" in prompt
        assert "manga" in prompt
        assert "4-panel" in prompt
        assert "Cat: Meow" in prompt

    def test_prompt_within_char_limit(self):
        panels = [{"scene": "x" * 200, "dialogue": "y" * 100}] * 6
        prompt = build_comic_prompt(
            slang="test", origin="test", explanation="test",
            panels=panels,
        )
        assert len(prompt) <= MAX_PROMPT_LENGTH

    def test_layout_description_varies_by_panel_count(self):
        p3 = [{"scene": "x", "dialogue": ""}] * 3
        p5 = [{"scene": "x", "dialogue": ""}] * 5
        p6 = [{"scene": "x", "dialogue": ""}] * 6

        prompt3 = build_comic_prompt("s", "o", "e", p3)
        prompt5 = build_comic_prompt("s", "o", "e", p5)
        prompt6 = build_comic_prompt("s", "o", "e", p6)

        assert "3-panel" in prompt3
        assert "5-panel" in prompt5
        assert "6-panel" in prompt6
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/backend/unit/test_prompts.py -v`

Expected: All PASS.

- [ ] **Step 5: Delete old prompts and commit**

```bash
git rm backend/app/prompts/analyze_prompt.py backend/app/prompts/compose_prompt.py
git add backend/app/prompts/script_prompt.py backend/app/prompts/comic_prompt.py tests/backend/unit/test_prompts.py
git commit -m "feat: add script/comic prompts, remove old analyze/compose prompts"
```

---

### Task 6: Backend Services (script_service, comic_service)

**Files:**
- Delete: `backend/app/services/analyze_service.py`
- Delete: `backend/app/services/generate_service.py`
- Create: `backend/app/services/script_service.py`
- Create: `backend/app/services/comic_service.py`
- Test: `tests/backend/unit/test_script_service.py` (new)
- Test: `tests/backend/unit/test_comic_service.py` (new)

- [ ] **Step 1: Write tests for script_service**

Create `tests/backend/unit/test_script_service.py`:

```python
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError
from app.services.script_service import generate_script


class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_valid_response_returns_script_data(self, mock_script_data, settings_mock):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.chat = AsyncMock(return_value=json.dumps(mock_script_data))

        with patch("app.services.script_service.LLMClient", return_value=mock_client):
            result = await generate_script(settings_mock)

        assert result["slang"] == "Break a leg"
        assert result["panel_count"] == 4
        assert len(result["panels"]) == 4
        mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_timeout_raises_script_error(self, settings_mock):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

        with patch("app.services.script_service.LLMClient", return_value=mock_client):
            with pytest.raises(LLMTimeoutError):
                await generate_script(settings_mock)

    @pytest.mark.asyncio
    async def test_llm_api_error_propagates(self, settings_mock):
        mock_client = MagicMock(spec=LLMClient)
        mock_client.chat = AsyncMock(side_effect=LLMApiError("4xx error"))

        with patch("app.services.script_service.LLMClient", return_value=mock_client):
            with pytest.raises(LLMApiError):
                await generate_script(settings_mock)
```

- [ ] **Step 2: Run tests — verify fail**

Run: `uv run pytest tests/backend/unit/test_script_service.py -v`

Expected: FAIL — module not found.

- [ ] **Step 3: Implement script_service.py**

```python
"""Script generation service — single LLM call for slang + comic script."""

import logging

from app.config import Settings
from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


async def generate_script(settings: Settings) -> dict:
    """Generate a random slang + 4-6 panel comic script.

    Returns parsed JSON dict with keys: slang, origin, explanation, panel_count, panels.
    Raises LLMTimeoutError or LLMApiError on failure.
    """
    llm = LLMClient(settings)

    content = await llm.chat(
        system_prompt=SCRIPT_SYSTEM_PROMPT,
        user_text="Please pick a random slang or idiom from any culture and create a comic script for it. Respond with JSON only.",
        temperature=0.9,
    )

    data = LLMClient.extract_json_from_content(content)

    # Validate structure
    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])

    if not (4 <= panel_count <= 6):
        raise ValueError(f"Invalid panel_count: {panel_count}, must be 4-6")
    if len(panels) != panel_count:
        raise ValueError(f"panels length ({len(panels)}) != panel_count ({panel_count})")

    logger.info(
        "Script generated: slang='%s', panels=%d",
        data.get("slang", "unknown"), panel_count,
    )

    return data
```

- [ ] **Step 4: Run tests — verify pass**

Run: `uv run pytest tests/backend/unit/test_script_service.py -v`

Expected: All PASS.

- [ ] **Step 5: Write tests for comic_service**

Create `tests/backend/unit/test_comic_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.image_gen_client import ImageGenClient, ImageGenApiError
from app.services.comic_service import generate_comic


class TestGenerateComic:
    @pytest.mark.asyncio
    async def test_valid_generation_returns_comic_data(
        self, mock_script_data, mock_comic_b64, settings_mock, tmp_data_dir
    ):
        """generate_comic should return comic_url, thumbnail_url, history_id."""
        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_comic_b64)

        with (
            patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
            patch("app.services.comic_service.FileStorage"),
        ):
            # Mock FileStorage instance
            from app.services.comic_service import FileStorage
            mock_storage = MagicMock()
            mock_storage.save_comic = MagicMock(return_value={
                "comic_url": "/data/comics/2026-04-01/test.png",
                "thumbnail_url": "/data/comics/2026-04-01/test_thumb.png",
            })
            FileStorage.return_value = mock_storage

            result = await generate_comic(mock_script_data, settings_mock)

        assert "comic_url" in result
        assert "thumbnail_url" in result
        assert "history_id" in result
        mock_img_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_within_800_chars(self, mock_script_data, settings_mock):
        """The built prompt should not exceed 800 characters."""
        from app.prompts.comic_prompt import build_comic_prompt
        prompt = build_comic_prompt(
            slang=mock_script_data["slang"],
            origin=mock_script_data["origin"],
            explanation=mock_script_data["explanation"],
            panels=mock_script_data["panels"],
        )
        assert len(prompt) <= 800

    @pytest.mark.asyncio
    async def test_image_gen_error_propagates(self, mock_script_data, settings_mock):
        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(
            side_effect=ImageGenApiError("API error")
        )

        with (
            patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
            patch("app.services.comic_service.FileStorage"),
        ):
            with pytest.raises(ImageGenApiError):
                await generate_comic(mock_script_data, settings_mock)
```

- [ ] **Step 6: Run tests — verify fail**

Run: `uv run pytest tests/backend/unit/test_comic_service.py -v`

Expected: FAIL — module not found.

- [ ] **Step 7: Implement comic_service.py**

```python
"""Comic generation service — build prompt + Qwen Image 2.0."""

import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.prompts.comic_prompt import build_comic_prompt
from app.services.image_gen_client import ImageGenClient
from app.storage.file_storage import FileStorage

logger = logging.getLogger(__name__)

COMIC_SIZE = "2688*1536"


async def generate_comic(script_data: dict, settings: Settings) -> dict:
    """Generate a comic strip image from script data.

    Args:
        script_data: Dict with keys slang, origin, explanation, panel_count, panels.
        settings: Application settings.

    Returns:
        Dict with comic_url, thumbnail_url, history_id.

    Raises:
        ImageGenApiError, ImageGenTimeoutError on failure.
    """
    # Build visual prompt
    prompt = build_comic_prompt(
        slang=script_data["slang"],
        origin=script_data["origin"],
        explanation=script_data["explanation"],
        panels=script_data["panels"],
    )

    logger.info("Generating comic for slang='%s' (prompt=%d chars)", script_data["slang"], len(prompt))

    # Generate image via Qwen Image 2.0 (text-to-image)
    img_client = ImageGenClient(settings)
    image_base64 = await img_client.generate_from_text(prompt=prompt, size=COMIC_SIZE)

    # Save to disk
    history_id = uuid.uuid4().hex
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    storage = FileStorage(settings.comic_storage_dir)
    urls = storage.save_comic(image_base64, history_id, date_str)

    logger.info("Comic saved: history_id=%s, url=%s", history_id, urls["comic_url"])

    return {
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "history_id": history_id,
    }
```

- [ ] **Step 8: Run tests**

Run: `uv run pytest tests/backend/unit/test_comic_service.py -v`

Expected: All PASS.

- [ ] **Step 9: Delete old services and commit**

```bash
git rm backend/app/services/analyze_service.py backend/app/services/generate_service.py
git add backend/app/services/script_service.py backend/app/services/comic_service.py tests/backend/unit/test_script_service.py tests/backend/unit/test_comic_service.py
git commit -m "feat: add script_service and comic_service, remove old analyze/generate services"
```

---

### Task 7: Backend Routers + main.py Update

**Files:**
- Delete: `backend/app/routers/analyze.py`
- Delete: `backend/app/routers/generate.py`
- Create: `backend/app/routers/script.py`
- Create: `backend/app/routers/comic.py`
- Modify: `backend/app/routers/history.py` (adapt fields)
- Modify: `backend/app/main.py` (swap routers, update lifespan)
- Test: `tests/backend/unit/test_script_route.py` (new)
- Test: `tests/backend/unit/test_comic_route.py` (new)
- Test: `tests/backend/unit/test_history.py` (adapt existing)

- [ ] **Step 1: Create router/script.py**

```python
"""POST /api/generate-script — Generate random slang + comic script."""

import logging

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.script import ScriptRequest, ScriptResponse, Panel
from app.services.llm_client import LLMTimeoutError, LLMApiError, LLMResponseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script"])


@router.post(
    "/generate-script",
    response_model=ApiResponse,
    responses={500: {"description": "LLM error"}},
)
async def generate_script_endpoint(
    request: ScriptRequest = ScriptRequest(),
    settings: Settings = Depends(get_settings),
):
    """Generate a random slang with a 4-6 panel comic script."""
    from app.services.script_service import generate_script

    try:
        data = await generate_script(settings)

        response_data = ScriptResponse(
            slang=data["slang"],
            origin=data["origin"],
            explanation=data["explanation"],
            panel_count=data["panel_count"],
            panels=[Panel(**p) for p in data["panels"]],
        )
        return ApiResponse(data=response_data.model_dump())

    except LLMTimeoutError as e:
        logger.error("Script generation timeout: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message=str(e), data=None)

    except (LLMResponseError, ValueError) as e:
        logger.error("Script generation invalid response: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_INVALID, message=str(e), data=None)

    except LLMApiError as e:
        logger.error("Script generation API error: %s", e)
        return ApiResponse(code=ErrorCode.SCRIPT_LLM_FAILED, message=str(e), data=None)

    except Exception as e:
        logger.exception("Script generation unexpected error")
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
```

- [ ] **Step 2: Create router/comic.py**

```python
"""POST /api/generate-comic — Generate comic strip image from script."""

import logging

from fastapi import APIRouter, Depends

from app.config import Settings
from app.dependencies import get_settings
from app.schemas.common import ApiResponse, ErrorCode
from app.schemas.comic import ComicRequest, ComicResponse
from app.services.image_gen_client import (
    ImageGenTimeoutError,
    ImageGenApiError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["comic"])


@router.post(
    "/generate-comic",
    response_model=ApiResponse,
    responses={500: {"description": "Image generation error"}},
)
async def generate_comic_endpoint(
    request: ComicRequest,
    settings: Settings = Depends(get_settings),
):
    """Generate a 16:9 comic strip image from the script."""
    from app.services.comic_service import generate_comic

    script_data = request.model_dump()

    try:
        data = await generate_comic(script_data, settings)

        response_data = ComicResponse(
            comic_url=data["comic_url"],
            thumbnail_url=data["thumbnail_url"],
            history_id=data["history_id"],
        )
        return ApiResponse(data=response_data.model_dump())

    except ImageGenTimeoutError as e:
        logger.error("Comic generation timeout: %s", e)
        return ApiResponse(code=ErrorCode.IMAGE_GEN_FAILED, message=str(e), data=None)

    except ImageGenApiError as e:
        logger.error("Comic generation API error: %s", e)
        return ApiResponse(code=ErrorCode.IMAGE_GEN_FAILED, message=str(e), data=None)

    except Exception as e:
        logger.exception("Comic generation unexpected error")
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
```

- [ ] **Step 3: Write router integration tests**

Create `tests/backend/unit/test_script_route.py`:

```python
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.llm_client import LLMClient


@pytest.mark.asyncio
async def test_generate_script_success(client, mock_script_data):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(return_value=json.dumps(mock_script_data))

    with patch("app.services.script_service.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["slang"] == "Break a leg"
    assert data["data"]["panel_count"] == 4
    assert len(data["data"]["panels"]) == 4


@pytest.mark.asyncio
async def test_generate_script_llm_timeout(client):
    from app.services.llm_client import LLMTimeoutError

    mock_client = MagicMock(spec=LLMClient)
    mock_client.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

    with patch("app.services.script_service.LLMClient", return_value=mock_client):
        resp = await client.post("/api/generate-script", json={})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50001  # SCRIPT_LLM_FAILED
```

Create `tests/backend/unit/test_comic_route.py`:

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.image_gen_client import ImageGenClient


@pytest.mark.asyncio
async def test_generate_comic_success(client, mock_script_data, mock_comic_b64):
    mock_img_client = MagicMock(spec=ImageGenClient)
    mock_img_client.generate_from_text = AsyncMock(return_value=mock_comic_b64)

    request_body = {
        "slang": mock_script_data["slang"],
        "origin": mock_script_data["origin"],
        "explanation": mock_script_data["explanation"],
        "panel_count": mock_script_data["panel_count"],
        "panels": mock_script_data["panels"],
    }

    with (
        patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
        patch("app.services.comic_service.FileStorage") as MockStorage,
    ):
        mock_storage = MagicMock()
        mock_storage.save_comic = MagicMock(return_value={
            "comic_url": "/data/comics/2026-04-01/test.png",
            "thumbnail_url": "/data/comics/2026-04-01/test_thumb.png",
        })
        MockStorage.return_value = mock_storage

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
```

- [ ] **Step 4: Update main.py**

Replace old router imports, update lifespan:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging
from app.middleware import RequestIdMiddleware
from app.routers import script, comic, history, traces


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.comic_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.history_file).parent.mkdir(parents=True, exist_ok=True)
    if settings.trace_enabled:
        Path(settings.trace_dir).mkdir(parents=True, exist_ok=True)
        from app.flow_log.trace_store import TraceStore
        TraceStore(settings.trace_dir, settings.trace_retention_days).cleanup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging(log_file="logs/backend.log", level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    data_dir = Path("data")
    if data_dir.exists():
        app.mount("/data", StaticFiles(directory="data"), name="data")
    app.include_router(script.router)
    app.include_router(comic.router)
    app.include_router(history.router)
    app.include_router(traces.router)
    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "SlangToon"}
```

- [ ] **Step 5: Update history router**

Read the existing `backend/app/routers/history.py` and update `HistoryItem` references to use the new schema fields (slang, origin, explanation, panel_count, comic_url, thumbnail_url, comic_prompt). The router logic should remain the same — it delegates to `history_service`.

- [ ] **Step 6: Update history test**

Update `tests/backend/unit/test_history.py` to use new field names. The test may create HistoryItem fixtures with old fields (style_name, poster_url, photo_url) — update to new fields.

- [ ] **Step 7: Delete old routers and run all backend tests**

```bash
git rm backend/app/routers/analyze.py backend/app/routers/generate.py
uv run pytest tests/backend/unit/ -v
```

Fix any remaining import errors (some tests may import from deleted modules like `app.services.analyze_service`).

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/ backend/app/main.py tests/backend/unit/test_script_route.py tests/backend/unit/test_comic_route.py tests/backend/unit/test_history.py
git commit -m "feat: add script/comic routers, update main.py and history for SlangToon"
```

---

### Task 8: Delete Old Backend Files + Clean Up

**Files:**
- Delete: `backend/app/schemas/analyze.py`
- Delete: `backend/app/schemas/generate.py`
- Delete: `tests/backend/unit/test_analyze.py`
- Delete: `tests/backend/unit/test_generate.py`
- Delete: `tests/backend/unit/test_system_prompt.py`
- Delete: `tests/backend/unit/test_schemas_common.py`
- Modify: `backend/app/prompts/__init__.py` (update exports if needed)
- Modify: `backend/app/schemas/__init__.py` (update exports if needed)
- Modify: `backend/app/services/__init__.py` (update exports if needed)

- [ ] **Step 1: Delete old files**

```bash
git rm backend/app/schemas/analyze.py backend/app/schemas/generate.py
git rm tests/backend/unit/test_analyze.py tests/backend/unit/test_generate.py
git rm tests/backend/unit/test_system_prompt.py tests/backend/unit/test_schemas_common.py
```

- [ ] **Step 2: Fix __init__.py files if they import deleted modules**

Check and update `backend/app/prompts/__init__.py`, `backend/app/schemas/__init__.py`, `backend/app/services/__init__.py`, `backend/app/routers/__init__.py` for any stale imports.

- [ ] **Step 3: Run full backend test suite**

Run: `uv run pytest tests/backend/unit/ -v`

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old analyze/generate schemas, tests, and stale imports"
```

---

### Task 9: Frontend Types, Constants, API Client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/constants/index.ts`
- Modify: `frontend/src/services/api.ts`
- Test: `frontend/src/services/api.test.ts` (adapt existing)

- [ ] **Step 1: Update types/index.ts**

```typescript
export enum AppState {
  CAMERA_READY = 'CAMERA_READY',
  SCRIPT_LOADING = 'SCRIPT_LOADING',
  SCRIPT_PREVIEW = 'SCRIPT_PREVIEW',
  COMIC_GENERATING = 'COMIC_GENERATING',
  COMIC_READY = 'COMIC_READY',
  HISTORY = 'HISTORY',
}

export type GestureType = 'ok' | 'open_palm' | 'none';

export interface Panel {
  scene: string;
  dialogue: string;
}

export interface ScriptData {
  slang: string;
  origin: string;
  explanation: string;
  panel_count: number;
  panels: Panel[];
}

export interface ScriptResponse {
  code: number;
  message: string;
  data: ScriptData;
}

export interface ComicResponse {
  code: number;
  message: string;
  data: {
    comic_url: string;
    thumbnail_url: string;
    history_id: string;
  };
}

export interface HistoryItem {
  id: string;
  slang: string;
  origin: string;
  explanation: string;
  panel_count: number;
  comic_url: string;
  thumbnail_url: string;
  comic_prompt: string;
  created_at: string;
}

export interface HistoryResponse {
  code: number;
  message: string;
  data: {
    items: HistoryItem[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  };
}
```

- [ ] **Step 2: Update constants/index.ts**

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const API_ENDPOINTS = {
  GENERATE_SCRIPT: '/api/generate-script',
  GENERATE_COMIC: '/api/generate-comic',
  HISTORY: '/api/history',
} as const;

export const TIMEOUTS = {
  SCRIPT_REQUEST: 200_000,
  COMIC_REQUEST: 400_000,
  HISTORY_REQUEST: 10_000,
} as const;
```

- [ ] **Step 3: Update services/api.ts**

Replace old `analyzePhoto` and `generatePoster` with new functions:

```typescript
import type { ScriptResponse, ComicResponse, HistoryResponse } from '../types';
import { API_BASE_URL, API_ENDPOINTS, TIMEOUTS } from '../constants';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function parseApiError(error: unknown): string {
  if (error instanceof ApiError) {
    return `Request failed (${error.status}): ${error.statusText}`;
  }
  if (error instanceof DOMException && error.name === 'TimeoutError') {
    return 'Request timed out, please retry';
  }
  if (error instanceof DOMException && error.name === 'AbortError') {
    return 'Request cancelled';
  }
  if (error instanceof TypeError) {
    return 'Network error, check connection';
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Unknown error';
}

async function request<T>(
  endpoint: string,
  options: RequestInit,
  timeoutMs: number,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const t0 = performance.now();

  try {
    const response = await fetch(url, {
      ...options,
      signal: AbortSignal.timeout(timeoutMs),
    });

    const traceId = response.headers.get('x-trace-id');
    console.log(
      '[FlowTrace] API response:',
      endpoint,
      '| trace_id:',
      traceId,
      '| status:',
      response.status,
      '| duration_ms:',
      Math.round(performance.now() - t0),
    );

    if (!response.ok) {
      throw new ApiError(
        `HTTP ${response.status}`,
        response.status,
        response.statusText,
      );
    }

    const data: T = await response.json();

    if (
      typeof data === 'object' &&
      data !== null &&
      'code' in data &&
      (data as { code: number }).code !== 0
    ) {
      const msg = 'message' in data
        ? String((data as { message: unknown }).message)
        : 'Server error';
      throw new ApiError(msg, response.status, msg);
    }

    return data;
  } catch (error) {
    throw new Error(parseApiError(error));
  }
}

export async function generateScript(): Promise<ScriptResponse> {
  return request<ScriptResponse>(
    API_ENDPOINTS.GENERATE_SCRIPT,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    },
    TIMEOUTS.SCRIPT_REQUEST,
  );
}

export async function generateComic(
  scriptData: {
    slang: string;
    origin: string;
    explanation: string;
    panel_count: number;
    panels: { scene: string; dialogue: string }[];
  },
): Promise<ComicResponse> {
  return request<ComicResponse>(
    API_ENDPOINTS.GENERATE_COMIC,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scriptData),
    },
    TIMEOUTS.COMIC_REQUEST,
  );
}

export async function getHistory(
  page: number,
  pageSize: number,
): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });

  return request<HistoryResponse>(
    `${API_ENDPOINTS.HISTORY}?${params.toString()}`,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    },
    TIMEOUTS.HISTORY_REQUEST,
  );
}
```

- [ ] **Step 4: Update api.test.ts**

Update existing API tests to use new function names (`generateScript`, `generateComic`) and remove old tests (`analyzePhoto`, `generatePoster`).

- [ ] **Step 5: Run frontend tests**

Run: `cd frontend && npx vitest run`

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/ frontend/src/constants/ frontend/src/services/
git commit -m "feat: update frontend types, constants, and API client for SlangToon"
```

---

### Task 10: Frontend Components (ScriptPreview, ComicDisplay, HistoryList)

**Files:**
- Delete: `frontend/src/components/StyleSelection/`, `StyleCard/`, `PosterDisplay/`, `GestureOverlay/`, `Countdown/`
- Delete: `frontend/src/utils/captureFrame.ts`
- Create: `frontend/src/components/ScriptPreview/ScriptPreview.tsx`
- Create: `frontend/src/components/ComicDisplay/ComicDisplay.tsx`
- Create: `frontend/src/components/HistoryList/HistoryList.tsx`

- [ ] **Step 1: Create ScriptPreview component**

Create `frontend/src/components/ScriptPreview/ScriptPreview.tsx`:

```tsx
import type { ScriptData } from '../../types';

interface ScriptPreviewProps {
  data: ScriptData;
  onShuffle: () => void;
  onGenerate: () => void;
  isLoading: boolean;
}

export default function ScriptPreview({ data, onShuffle, onGenerate, isLoading }: ScriptPreviewProps) {
  return (
    <div className="w-full max-w-3xl px-6 py-8">
      {/* Slang title card */}
      <div className="bg-gray-800 rounded-xl p-6 mb-6">
        <h2 className="text-2xl font-bold text-yellow-400 mb-2">"{data.slang}"</h2>
        <p className="text-gray-400 text-sm mb-1">
          Origin: <span className="text-gray-300">{data.origin}</span>
        </p>
        <p className="text-gray-300">{data.explanation}</p>
      </div>

      {/* Panel descriptions */}
      <div className="space-y-3 mb-8">
        {data.panels.map((panel, i) => (
          <div key={i} className="bg-gray-800/50 rounded-lg p-4 border-l-4 border-indigo-500">
            <p className="text-gray-400 text-xs mb-1">Panel {i + 1}</p>
            <p className="text-gray-200">{panel.scene}</p>
            {panel.dialogue && (
              <p className="text-yellow-300/80 text-sm mt-1 italic">{panel.dialogue}</p>
            )}
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div className="flex gap-4 justify-center">
        <button
          onClick={onShuffle}
          disabled={isLoading}
          className="px-6 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Shuffle
        </button>
        <button
          onClick={onGenerate}
          disabled={isLoading}
          className="px-6 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Generate Comic
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create ComicDisplay component**

Create `frontend/src/components/ComicDisplay/ComicDisplay.tsx`:

```tsx
interface ComicDisplayProps {
  comicUrl: string;
  slang: string;
  onNew: () => void;
  onGoToHistory: () => void;
}

export default function ComicDisplay({ comicUrl, slang, onNew, onGoToHistory }: ComicDisplayProps) {
  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = comicUrl;
    link.download = `slangtoon-${slang.replace(/\s+/g, '-').toLowerCase()}.png`;
    link.click();
  };

  return (
    <div className="w-full max-w-4xl px-6 py-8">
      {/* Comic title */}
      <h2 className="text-xl font-bold text-yellow-400 mb-4 text-center">"{slang}"</h2>

      {/* Comic image */}
      <div className="rounded-xl overflow-hidden shadow-2xl border border-gray-700">
        <img
          src={comicUrl}
          alt={`Comic strip for "${slang}"`}
          className="w-full h-auto"
        />
      </div>

      {/* Action buttons */}
      <div className="flex gap-4 justify-center mt-6">
        <button
          onClick={handleDownload}
          className="px-6 py-3 bg-green-600 rounded-lg hover:bg-green-500 transition-colors"
        >
          Download
        </button>
        <button
          onClick={onGoToHistory}
          className="px-6 py-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
        >
          History
        </button>
        <button
          onClick={onNew}
          className="px-6 py-3 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition-colors"
        >
          New Slang
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create HistoryList component (rewrite)**

Create `frontend/src/components/HistoryList/HistoryList.tsx`:

```tsx
import type { HistoryItem } from '../../types';
import ErrorDisplay from '../ErrorDisplay';

interface HistoryListProps {
  items: HistoryItem[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onBack: () => void;
}

export default function HistoryList({ items, isLoading, error, onRetry, onBack }: HistoryListProps) {
  if (error) {
    return (
      <div className="w-full max-w-4xl px-6 py-8">
        <ErrorDisplay message={error} onRetry={onRetry} retryText="Retry" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl px-6 py-8">
      <button
        onClick={onBack}
        className="mb-6 px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
      >
        Back
      </button>

      <h2 className="text-xl font-bold mb-6">History</h2>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <div className="h-12 w-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <p className="text-gray-500 text-center py-16">No comics generated yet.</p>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <div key={item.id} className="bg-gray-800 rounded-lg p-4 flex gap-4">
              <img
                src={item.thumbnail_url}
                alt={item.slang}
                className="w-24 h-16 object-cover rounded"
              />
              <div className="flex-1 min-w-0">
                <h3 className="text-yellow-400 font-medium truncate">"{item.slang}"</h3>
                <p className="text-gray-400 text-sm">{item.origin} · {item.panel_count} panels</p>
                <p className="text-gray-500 text-xs mt-1">{item.created_at}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Delete old frontend components**

```bash
git rm -r frontend/src/components/StyleSelection/
git rm -r frontend/src/components/StyleCard/
git rm -r frontend/src/components/PosterDisplay/
git rm -r frontend/src/components/GestureOverlay/
git rm -r frontend/src/components/Countdown/
git rm frontend/src/utils/captureFrame.ts
```

Also delete their test files if they exist (check for `*.test.tsx` / `*.test.ts` alongside deleted components).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ScriptPreview/ frontend/src/components/ComicDisplay/ frontend/src/components/HistoryList/
git commit -m "feat: add ScriptPreview, ComicDisplay, HistoryList components; remove old components"
```

---

### Task 11: Frontend App.tsx State Machine Rewrite

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Rewrite App.tsx with new state machine**

```tsx
import { useRef, useState, useEffect, useCallback } from 'react';
import { AppState } from './types';
import type { GestureType, ScriptData, HistoryItem } from './types';
import { useCamera } from './hooks/useCamera';
import { useGestureDetector } from './hooks/useGestureDetector';
import { useMediaPipeHands } from './hooks/useMediaPipeHands';
import { generateScript, generateComic, getHistory } from './services/api';
import CameraView from './components/CameraView/CameraView';
import ScriptPreview from './components/ScriptPreview/ScriptPreview';
import ComicDisplay from './components/ComicDisplay/ComicDisplay';
import HistoryList from './components/HistoryList/HistoryList';
import ErrorDisplay from './components/ErrorDisplay';
import LoadingSpinner from './components/LoadingSpinner';

function App() {
  // ── State machine ──────────────────────────────────────────
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [scriptData, setScriptData] = useState<ScriptData | null>(null);
  const [comicUrl, setComicUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [gesture, setGesture] = useState<GestureType>('none');
  const [gestureConfidence, setGestureConfidence] = useState<number>(0);
  const [historyLoading, setHistoryLoading] = useState(false);

  const appStateRef = useRef<AppState>(appState);
  useEffect(() => {
    appStateRef.current = appState;
  }, [appState]);

  // ── Navigation helpers ─────────────────────────────────────
  const goHome = useCallback(() => {
    setScriptData(null);
    setComicUrl('');
    setAppState(AppState.CAMERA_READY);
  }, []);

  const goHistory = useCallback(() => {
    setError(null);
    setAppState(AppState.HISTORY);
  }, []);

  // ── Camera hook ────────────────────────────────────────────
  const { videoRef, isReady, error: cameraError, restart: restartCamera } = useCamera();

  // ── Gesture handling ───────────────────────────────────────
  const onGestureDetected = useCallback(
    (event: { gesture: GestureType; confidence: number }) => {
      setGesture(event.gesture);
      setGestureConfidence(event.confidence);

      const state = appStateRef.current;

      // OK gesture → generate script
      if (event.gesture === 'ok' && state === AppState.CAMERA_READY) {
        handleGenerateScript();
        return;
      }

      // Open palm → go home
      if (event.gesture === 'open_palm' && state !== AppState.COMIC_READY) {
        goHome();
      }
    },
    [goHome],
  );

  const { processLandmarks } = useGestureDetector({ onGestureDetected });

  const handleMediaPipeResults = useCallback(
    (landmarks: { x: number; y: number; z: number }[]) => {
      if (landmarks.length > 0) {
        processLandmarks(landmarks);
      }
    },
    [processLandmarks],
  );

  const { canvasRef } = useMediaPipeHands({
    videoRef,
    onResults: handleMediaPipeResults,
  });

  // ── Script generation ──────────────────────────────────────
  const handleGenerateScript = useCallback(async () => {
    setError(null);
    setAppState(AppState.SCRIPT_LOADING);

    try {
      const response = await generateScript();
      setScriptData(response.data);
      setAppState(AppState.SCRIPT_PREVIEW);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate script';
      setError(msg);
      setAppState(AppState.CAMERA_READY);
    }
  }, []);

  // ── Comic generation ───────────────────────────────────────
  const handleGenerateComic = useCallback(async () => {
    if (!scriptData) return;

    setError(null);
    setAppState(AppState.COMIC_GENERATING);

    try {
      const response = await generateComic({
        slang: scriptData.slang,
        origin: scriptData.origin,
        explanation: scriptData.explanation,
        panel_count: scriptData.panel_count,
        panels: scriptData.panels,
      });
      setComicUrl(response.data.comic_url);
      setAppState(AppState.COMIC_READY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate comic';
      setError(msg);
      setAppState(AppState.SCRIPT_PREVIEW);
    }
  }, [scriptData]);

  // ── History ────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    setError(null);
    try {
      const response = await getHistory(1, 20);
      setHistoryItems(response.data.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load history';
      setError(msg);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    if (appState === AppState.HISTORY) {
      fetchHistory();
    }
  }, [appState, fetchHistory]);

  // ── Render ─────────────────────────────────────────────────
  const showCamera = appState === AppState.CAMERA_READY;

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-gray-800 shrink-0">
        <h1
          className="text-xl font-bold cursor-pointer select-none"
          onClick={goHome}
        >
          SlangToon
        </h1>
        <button
          className="px-4 py-2 text-sm bg-gray-700 rounded hover:bg-gray-600 transition-colors"
          onClick={goHistory}
        >
          History
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center overflow-auto">
        {/* Camera view */}
        {showCamera && (
          <div className="relative w-full max-w-3xl aspect-video bg-gray-800 rounded-xl overflow-hidden">
            <CameraView
              videoRef={videoRef}
              canvasRef={canvasRef}
              className={`w-full h-full ${isReady ? '' : 'invisible'}`}
            />
            {!isReady && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                {cameraError ? (
                  <ErrorDisplay message={cameraError} onRetry={restartCamera} retryText="Restart Camera" />
                ) : (
                  <p className="text-gray-400">Starting camera...</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Gesture hint */}
        {showCamera && isReady && (
          <div className="mt-4 text-center">
            {error && <p className="text-red-400 text-sm mb-2">{error}</p>}
            <p className="text-gray-400 text-sm">
              Show <span className="text-green-400 font-medium">OK sign</span> to generate
              &nbsp;&middot;&nbsp;
              Show <span className="text-green-400 font-medium">open palm</span> to go back
            </p>
          </div>
        )}

        {/* Loading states */}
        {(appState === AppState.SCRIPT_LOADING || appState === AppState.COMIC_GENERATING) && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            {error ? (
              <ErrorDisplay
                message={error}
                onRetry={
                  appState === AppState.SCRIPT_LOADING
                    ? goHome
                    : handleGenerateComic
                }
                retryText="Retry"
              />
            ) : (
              <>
                <LoadingSpinner />
                <p className="text-gray-400 text-lg">
                  {appState === AppState.SCRIPT_LOADING
                    ? 'Creating something fun...'
                    : 'Drawing your comic...'}
                </p>
              </>
            )}
          </div>
        )}

        {/* Script preview */}
        {appState === AppState.SCRIPT_PREVIEW && scriptData && (
          <ScriptPreview
            data={scriptData}
            onShuffle={handleGenerateScript}
            onGenerate={handleGenerateComic}
            isLoading={false}
          />
        )}

        {/* Comic display */}
        {appState === AppState.COMIC_READY && (
          <ComicDisplay
            comicUrl={comicUrl}
            slang={scriptData?.sllang ?? ''}
            onNew={goHome}
            onGoToHistory={goHistory}
          />
        )}

        {/* History */}
        {appState === AppState.HISTORY && (
          <HistoryList
            items={historyItems}
            isLoading={historyLoading}
            error={error}
            onRetry={fetchHistory}
            onBack={goHome}
          />
        )}
      </main>
    </div>
  );
}

export default App;
```

- [ ] **Step 2: Run frontend tests and build**

Run: `cd frontend && npx vitest run && npm run build`

Fix any type errors or test failures.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: rewrite App.tsx with SlangToon state machine"
```

---

### Task 12: Update Documentation + Final Verification

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.env.example` (if needed)
- Modify: `README.md`

- [ ] **Step 1: Update CLAUDE.md**

Update the project name from "MagicPose" to "SlangToon", update project structure, API endpoints, error codes, state machine description, and workflow to match the new design spec.

- [ ] **Step 2: Run full test suites**

```bash
uv run pytest tests/backend/unit/ -v
cd frontend && npx vitest run
cd frontend && npm run build
```

All must pass.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md README.md .env.example
git commit -m "docs: update CLAUDE.md and README for SlangToon"
```
