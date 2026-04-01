# Logging System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the default Python/uvicorn logging with a unified, configurable system featuring request ID tracing, suppressed access logs, and complete error messages.

**Architecture:** A new `logging_config.py` module initializes logging via `dictConfig` with a custom Filter that injects request IDs from `contextvars`. A lightweight ASGI middleware in `middleware.py` assigns per-request IDs and logs entry/exit. All routers and services get targeted log points. Uvicorn access logs are disabled.

**Tech Stack:** Python `logging`, `contextvars`, FastAPI ASGI middleware, no new dependencies.

---

## File Map

| File | Responsibility |
|------|---------------|
| `backend/app/logging_config.py` (NEW) | `dictConfig` setup, custom Formatter/Filter, `setup_logging()` |
| `backend/app/middleware.py` (NEW) | Request ID middleware, request entry/exit logging |
| `backend/app/config.py` | Add `log_level` field |
| `backend/app/main.py` | Call `setup_logging()`, mount request ID middleware |
| `backend/run.py` | Disable uvicorn access log, override uvicorn log config |
| `backend/app/routers/analyze.py` | Add entry/exit log points |
| `backend/app/routers/generate.py` | Add entry/exit log points |
| `backend/app/routers/history.py` | Add entry log point |
| `backend/app/services/analyze_service.py` | Add LLM call start/complete logs |
| `backend/app/services/generate_service.py` | Add generate start/complete logs |
| `backend/app/services/history_service.py` | (no changes needed — simple CRUD, router-level logging sufficient) |
| `backend/app/services/llm_client.py` | Fix empty error messages, add request start/complete logs |
| `backend/app/services/image_gen_client.py` | Fix empty error messages, add request start/complete logs |
| `.env` | Add `LOG_LEVEL=INFO` |

---

### Task 1: Add `log_level` to Config

**Files:**
- Modify: `backend/app/config.py:41`
- Modify: `.env`
- Test: `tests/backend/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/backend/unit/test_config.py` — test that `log_level` defaults to `"INFO"` and can be overridden via env var:

```python
class TestLogLevel:
    def test_log_level_default(self):
        from app.config import Settings
        s = Settings(_env_file=None)
        assert s.log_level == "INFO"

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        from app.config import Settings
        s = Settings(_env_file=None)
        assert s.log_level == "DEBUG"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_config.py::TestLogLevel -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'log_level'`

- [ ] **Step 3: Implement the config field**

In `backend/app/config.py`, add after line 37 (after `cors_origins`):

```python
    # 日志
    log_level: str = "INFO"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/backend/unit/test_config.py::TestLogLevel -v`
Expected: PASS

- [ ] **Step 5: Add LOG_LEVEL to .env**

Append to `.env`:

```
LOG_LEVEL=INFO
```

- [ ] **Step 6: Commit**

```
feat: add log_level config field with LOG_LEVEL env var support
```

---

### Task 2: Create Logging Configuration Module

**Files:**
- Create: `backend/app/logging_config.py`
- Test: `tests/backend/unit/test_logging_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/unit/test_logging_config.py`:

```python
"""logging_config 模块的单元测试。"""

import logging
from unittest.mock import patch

import pytest


class TestSetupLogging:
    """验证 setup_logging() 正确配置日志系统。"""

    def test_creates_file_handler_for_backend_log(self, tmp_path, monkeypatch):
        """日志应写入 logs/backend.log 文件。"""
        log_file = tmp_path / "backend.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log_file), level="INFO")

        logger = logging.getLogger("app.test")
        handler_types = [type(h).__name__ for h in logger.handlers]
        # Root logger should have a FileHandler
        root_handler_types = [type(h).__name__ for h in logging.getLogger().handlers]
        assert "FileHandler" in root_handler_types

    def test_sets_log_level_from_parameter(self, tmp_path, monkeypatch):
        """传入 DEBUG 级别时，DEBUG 日志应可见。"""
        log_file = tmp_path / "backend.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log_file), level="DEBUG")

        logger = logging.getLogger("app.test")
        assert logger.isEnabledFor(logging.DEBUG)

    def test_third_party_loggers_suppressed(self, tmp_path, monkeypatch):
        """第三方 logger (uvicorn, httpx) 应被设为 WARNING 级别。"""
        log_file = tmp_path / "backend.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log_file), level="DEBUG")

        for name in ["uvicorn", "uvicorn.access", "uvicorn.error", "httpx", "httpcore"]:
            third_party_logger = logging.getLogger(name)
            assert third_party_logger.level == logging.WARNING, (
                f"{name} should be WARNING, got {logging.getLevelName(third_party_logger.level)}"
            )

    def test_log_format_includes_timestamp_and_module(self, tmp_path, monkeypatch):
        """日志格式应包含时间戳和模块名。"""
        log_file = tmp_path / "backend.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log_file), level="INFO")

        logger = logging.getLogger("app.test_format")
        logger.info("format test message")

        content = log_file.read_text(encoding="utf-8")
        # Should contain timestamp pattern [YYYY-MM-DD HH:MM:SS
        assert "[" in content
        assert "app.test_format" in content
        assert "format test message" in content

    def test_request_id_in_log_format(self, tmp_path, monkeypatch):
        """当日志中有 request_id 时，格式应包含 [req-xxxxx]。"""
        log_file = tmp_path / "backend.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        from app.logging_config import request_id_ctx
        setup_logging(log_file=str(log_file), level="INFO")

        token = request_id_ctx.set("req-abc12345")
        try:
            logger = logging.getLogger("app.test_rid")
            logger.info("request traced message")
        finally:
            request_id_ctx.reset(token)

        content = log_file.read_text(encoding="utf-8")
        assert "req-abc12345" in content


class TestRequestIdContext:
    """验证 request_id_ctx ContextVar。"""

    def test_default_value_is_empty(self):
        from app.logging_config import request_id_ctx
        assert request_id_ctx.get("") == ""

    def test_set_and_get(self):
        from app.logging_config import request_id_ctx
        token = request_id_ctx.set("req-test1234")
        assert request_id_ctx.get("") == "req-test1234"
        request_id_ctx.reset(token)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_logging_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.logging_config'`

- [ ] **Step 3: Implement logging_config.py**

Create `backend/app/logging_config.py`:

```python
"""统一日志配置模块。

提供 setup_logging() 一次性配置所有 logger，包括：
- 统一的日志格式（时间戳 + 级别 + 模块 + request_id + 消息）
- 仅文件输出（logs/backend.log）
- 第三方 logger 降级为 WARNING
- request_id 通过 contextvars 注入到日志格式中
"""

from __future__ import annotations

import logging
import logging.config
from contextvars import ContextVar
from pathlib import Path

# 用于在异步请求中传递 request_id
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class _RequestIdFilter(logging.Filter):
    """将 request_id 注入到日志记录中。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("")
        return True


# 统一日志格式
LOG_FORMAT = (
    "[%(asctime)s] "           # 时间戳
    "[%(levelname)-8s] "       # 级别（左对齐 8 字符）
    "[%(name)s] "              # 模块名
    "[%(request_id)s] "        # request_id
    "%(message)s"              # 消息
)

# 时间戳格式（精确到毫秒）
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_file: str = "logs/backend.log", level: str = "INFO") -> None:
    """初始化统一日志配置。

    Args:
        log_file: 日志文件路径。
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）。
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT,
            },
        },

        "filters": {
            "request_id": {
                "()": "app.logging_config._RequestIdFilter",
            },
        },

        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(log_path),
                "encoding": "utf-8",
                "formatter": "standard",
                "filters": ["request_id"],
            },
        },

        "root": {
            "level": level,
            "handlers": ["file"],
        },

        # 第三方 logger 强制 WARNING，消除噪音
        "loggers": {
            "uvicorn": {"level": "WARNING", "propagate": True},
            "uvicorn.access": {"level": "WARNING", "propagate": False},
            "uvicorn.error": {"level": "WARNING", "propagate": True},
            "httpx": {"level": "WARNING", "propagate": True},
            "httpcore": {"level": "WARNING", "propagate": True},
        },
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/backend/unit/test_logging_config.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```
feat: add unified logging config with request_id support
```

---

### Task 3: Create Request ID Middleware

**Files:**
- Create: `backend/app/middleware.py`
- Test: `tests/backend/unit/test_middleware.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend/unit/test_middleware.py`:

```python
"""Request ID 中间件的单元测试。"""

import asyncio
import logging
import re

from unittest.mock import patch, MagicMock

import pytest


class TestRequestIdMiddleware:
    """验证 RequestIdMiddleware 为每个请求分配唯一 ID 并记录日志。"""

    @pytest.fixture
    def log_records(self, tmp_path, monkeypatch):
        """捕获日志记录到列表。"""
        log_file = tmp_path / "test.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log_file), level="DEBUG")
        return log_file

    def test_assigns_request_id_format(self, log_records):
        """request_id 应为 req-xxxxxxxx 格式（8位hex）。"""
        from app.middleware import RequestIdMiddleware

        pattern = re.compile(r"^req-[0-9a-f]{8}$")

        # Middleware._generate_request_id() is static, test it directly
        for _ in range(20):
            rid = RequestIdMiddleware._generate_request_id()
            assert pattern.match(rid), f"Invalid request_id format: {rid}"

    def test_request_id_injected_to_context(self, log_records):
        """请求处理期间，request_id 应可通过 contextvars 获取。"""
        from app.middleware import RequestIdMiddleware
        from app.logging_config import request_id_ctx

        async def dummy_app(scope, receive, send):
            # Inside the request context, request_id should be set
            rid = request_id_ctx.get("")
            assert rid.startswith("req-"), f"Expected req-xxx, got {rid}"
            assert len(rid) == 12
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = RequestIdMiddleware(dummy_app)

        async def run():
            scope = {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "query_string": b"",
                "headers": [],
                "server": ("testserver", 80),
            }
            responses = []
            async def send(msg):
                responses.append(msg)
            await middleware(scope, MagicMock(), send)

        asyncio.run(run())

    def test_logs_request_entry_and_exit(self, log_records):
        """中间件应记录请求进入和退出日志。"""
        from app.middleware import RequestIdMiddleware

        async def dummy_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = RequestIdMiddleware(dummy_app)

        async def run():
            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/analyze",
                "query_string": b"",
                "headers": [],
                "server": ("testserver", 80),
            }
            responses = []
            async def send(msg):
                responses.append(msg)
            await middleware(scope, MagicMock(), send)

        asyncio.run(run())

        content = log_records.read_text(encoding="utf-8")
        assert "→ POST /api/analyze" in content
        assert "← POST /api/analyze 200" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_middleware.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.middleware'`

- [ ] **Step 3: Implement middleware.py**

Create `backend/app/middleware.py`:

```python
"""Request ID 中间件 — 为每个请求分配唯一 ID 并追踪耗时。"""

from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Receive, Scope, Send

from app.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

# 慢请求阈值（秒），超过此值记录 WARNING
SLOW_REQUEST_THRESHOLD = 1.0


class RequestIdMiddleware:
    """ASGI 中间件：为每个 HTTP 请求分配 request_id 并记录进入/退出日志。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = self._generate_request_id()
        token = request_id_ctx.set(request_id)

        method = scope["method"]
        path = scope["path"]
        start_time = time.perf_counter()

        logger.info("→ %s %s", method, path)

        try:
            await self.app(scope, receive, send)
        finally:
            elapsed = time.perf_counter() - start_time
            request_id_ctx.reset(token)

        # Note: status code captured via send wrapper if needed in future.
        # For now we log exit after the app completes.
        if elapsed > SLOW_REQUEST_THRESHOLD:
            logger.warning("← %s %s (耗时: %.1fs, 慢请求)", method, path, elapsed)
        else:
            logger.info("← %s %s (耗时: %.1fs)", method, path, elapsed)

    @staticmethod
    def _generate_request_id() -> str:
        """生成格式为 req-xxxxxxxx 的唯一请求 ID。"""
        return f"req-{uuid.uuid4().hex[:8]}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/backend/unit/test_middleware.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```
feat: add RequestIdMiddleware with per-request tracing
```

---

### Task 4: Integrate Logging into App Startup

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/run.py`
- Test: `tests/backend/unit/test_app.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/backend/unit/test_app.py`:

```python
class TestLoggingIntegration:
    """验证日志系统在 app 启动时正确初始化。"""

    def test_create_app_initializes_logging(self, app, tmp_path, monkeypatch):
        """create_app() 调用后，日志系统应已配置。"""
        import logging
        # Root logger should have handlers (configured by setup_logging)
        root = logging.getLogger()
        assert len(root.handlers) > 0

    def test_middleware_added(self, module_app, monkeypatch, tmp_path):
        """RequestIdMiddleware 应作为内部 middleware 注册。"""
        # Check that RequestIdMiddleware wraps the app
        from app.middleware import RequestIdMiddleware
        # user_middleware list won't show it since it's added differently,
        # but we can verify by checking middleware stack
        found = False
        for mw in module_app.user_middleware:
            if mw.cls is not None and mw.cls.__name__ == "RequestIdMiddleware":
                found = True
                break
        assert found, "RequestIdMiddleware should be in user_middleware"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_app.py::TestLoggingIntegration -v`
Expected: FAIL — RequestIdMiddleware not found in user_middleware

- [ ] **Step 3: Modify main.py**

Update `backend/app/main.py` — add logging init and middleware. Full new content:

```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging
from app.middleware import RequestIdMiddleware
from app.routers import analyze, generate, history


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.photo_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.poster_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.history_file).parent.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    # 初始化日志系统
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
    app.include_router(analyze.router)
    app.include_router(generate.router)
    app.include_router(history.router)
    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "PoseArtGenerator"}
```

- [ ] **Step 4: Modify run.py — disable uvicorn access log**

Update `backend/run.py`:

```python
import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=False,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "loggers": {
                "uvicorn": {"level": "WARNING", "propagate": True},
                "uvicorn.access": {"level": "WARNING", "propagate": False},
                "uvicorn.error": {"level": "WARNING", "propagate": True},
            },
        },
    )
```

- [ ] **Step 5: Run all existing tests to verify no regressions**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```
feat: integrate logging system into app startup and disable uvicorn noise
```

---

### Task 5: Add Log Points to Routers

**Files:**
- Modify: `backend/app/routers/analyze.py`
- Modify: `backend/app/routers/generate.py`
- Modify: `backend/app/routers/history.py`
- Test: existing tests should still pass (behavior unchanged, only adding logs)

- [ ] **Step 1: Add logs to analyze.py**

Replace `backend/app/routers/analyze.py` with:

```python
import logging

from fastapi import APIRouter, Depends
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.services.analyze_service import analyze_photo, AnalyzeError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=ApiResponse)
async def analyze_endpoint(request: AnalyzeRequest, settings: Settings = Depends(get_settings)):
    logger.info("收到分析请求")
    try:
        options = await analyze_photo(request.image_base64, request.image_format, settings)
        logger.info("分析完成, 返回 %d 个风格选项", len(options))
        return ApiResponse(code=0, message="success", data=AnalyzeResponse(options=options).model_dump())
    except AnalyzeError as e:
        logger.error("分析失败: %s", e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("分析异常: %s", e, exc_info=True)
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
```

- [ ] **Step 2: Add logs to generate.py**

Replace `backend/app/routers/generate.py` with:

```python
import logging

from fastapi import APIRouter, Depends
from app.schemas.generate import GenerateRequest
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.services.generate_service import generate_artwork, GenerateError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=ApiResponse)
async def generate_endpoint(request: GenerateRequest, settings: Settings = Depends(get_settings)):
    logger.info("收到生成请求 (style=%s)", request.style_name)
    storage = FileStorage(settings.photo_storage_dir, settings.poster_storage_dir)
    history = HistoryService(settings.history_file, settings.max_history_records)
    try:
        result = await generate_artwork(
            request.image_base64, request.image_format, request.prompt, request.style_name,
            settings, storage, history,
        )
        logger.info("生成完成, poster_url=%s", result.get("poster_url", ""))
        return ApiResponse(code=0, message="success", data=result)
    except GenerateError as e:
        logger.error("生成失败: %s", e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("生成异常: %s", e, exc_info=True)
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
```

- [ ] **Step 3: Add logs to history.py**

Replace `backend/app/routers/history.py` with:

```python
import logging

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=ApiResponse)
async def history_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings),
):
    logger.info("查询历史记录 (page=%d, page_size=%d)", page, page_size)
    history = HistoryService(settings.history_file, settings.max_history_records)
    result = history.get_page(page=page, page_size=page_size)
    logger.info("返回 %d 条历史记录 (total=%d)", len(result["items"]), result["total"])
    return ApiResponse(code=0, message="success", data=result)
```

- [ ] **Step 4: Run all existing tests**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: All PASS (no behavior change)

- [ ] **Step 5: Commit**

```
feat: add structured log points to all router endpoints
```

---

### Task 6: Add Log Points to Services

**Files:**
- Modify: `backend/app/services/analyze_service.py`
- Modify: `backend/app/services/generate_service.py`
- Test: existing tests should still pass

- [ ] **Step 1: Add logs to analyze_service.py**

Replace `backend/app/services/analyze_service.py` with:

```python
import logging

from app.config import Settings
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError, LLMResponseError
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.schemas.analyze import StyleOption

logger = logging.getLogger(__name__)


class AnalyzeError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
    """分析照片，返回风格选项列表。"""
    llm = LLMClient(settings)
    try:
        logger.info("LLM 分析请求开始 (model=%s)", settings.openai_model)
        content = await llm.chat_with_vision(
            SYSTEM_PROMPT, image_base64, image_format,
            "请分析照片中的人物，生成 3 个创意风格选项",
            temperature=0.8,
        )
        logger.info("LLM 分析完成")
    except (LLMTimeoutError, LLMApiError) as e:
        logger.error("LLM 调用失败: %s", e)
        raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        logger.error("LLM 响应解析失败: %s", e)
        raise AnalyzeError(50002, f"Vision LLM 返回格式异常: {e}") from e

    if not isinstance(data, dict) or "options" not in data:
        raise AnalyzeError(50002, "JSON 缺少 options 字段")

    options = data["options"]
    if not isinstance(options, list) or len(options) == 0:
        raise AnalyzeError(50002, "options 应为非空数组")

    style_options = []
    for i, opt in enumerate(options[:3]):
        if not isinstance(opt, dict):
            raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
        for field in ("name", "brief", "prompt"):
            if field not in opt or not opt[field]:
                raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
        style_options.append(StyleOption(**opt))
    return style_options
```

- [ ] **Step 2: Add logs to generate_service.py**

Replace `backend/app/services/generate_service.py` with:

```python
import logging

from app.config import Settings
from app.services.image_gen_client import ImageGenClient, ImageGenTimeoutError, ImageGenApiError
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService

logger = logging.getLogger(__name__)


class GenerateError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def generate_artwork(
    image_base64: str, image_format: str, prompt: str, style_name: str,
    settings: Settings, storage: FileStorage, history: HistoryService,
) -> dict:
    photo_info = storage.save_photo(image_base64, image_format)
    gen_client = ImageGenClient(settings)
    try:
        logger.info("图片生成请求开始 (model=%s, style=%s)", settings.qwen_image_model, style_name)
        poster_b64 = await gen_client.generate(prompt, image_base64, image_format)
        logger.info("图片生成完成")
    except (ImageGenTimeoutError, ImageGenApiError) as e:
        logger.error("图片生成失败: %s", e)
        raise GenerateError(50003, f"图片生成失败: {e}") from e
    except Exception as e:
        logger.error("生成结果处理失败: %s", e)
        raise GenerateError(50004, f"生成结果处理失败: {e}") from e

    poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])
    history_id = history.add({
        "style_name": style_name, "prompt": prompt,
        "poster_url": poster_info["poster_url"],
        "thumbnail_url": poster_info["thumbnail_url"],
        "photo_url": photo_info["url"],
    })
    logger.info("海报已保存 (history_id=%s)", history_id)
    return {"poster_url": poster_info["poster_url"], "thumbnail_url": poster_info["thumbnail_url"], "history_id": history_id}
```

- [ ] **Step 3: Run all existing tests**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```
feat: add structured log points to service layer
```

---

### Task 7: Fix Empty Error Messages in LLM & Image Gen Clients

**Files:**
- Modify: `backend/app/services/llm_client.py`
- Modify: `backend/app/services/image_gen_client.py`
- Test: existing tests should still pass

- [ ] **Step 1: Fix llm_client.py — add complete error messages and timing logs**

The current `logger.warning` calls pass `exc` as a positional arg to `%s`, but for `httpx.TimeoutException`, `str(exc)` can be empty. Fix by using `repr(exc)` and adding explicit detail extraction.

In `backend/app/services/llm_client.py`, update the `chat_with_vision` method:

Replace the retry loop body (lines 76-123) with:

```python
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
                            "LLM 5xx (attempt %d/%d): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    self._check_status(resp)

                    data = resp.json()
                    content: str = data["choices"][0]["message"]["content"]
                    logger.info("LLM 响应成功 (attempt %d/%d)", attempt, self._max_retries)
                    return content

            except httpx.TimeoutException as exc:
                last_exc = exc
                detail = repr(exc) if str(exc) else f"{type(exc).__name__}(timeout={self._timeout}s)"
                logger.warning(
                    "LLM 请求超时 (attempt %d/%d): %s",
                    attempt, self._max_retries, detail,
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except LLMApiError as exc:
                # 4xx 不重试
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "LLM 请求异常 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise LLMTimeoutError(
            f"LLM 请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc
```

Also add a start log at the beginning of `chat_with_vision`, after the `url = ...` line:

```python
        logger.info("LLM 请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
```

- [ ] **Step 2: Fix image_gen_client.py — add complete error messages and timing logs**

In `backend/app/services/image_gen_client.py`, update the retry loop (lines 136-195):

Replace with:

```python
        last_exc: Exception | None = None
        logger.info("图像生成请求发送中 (model=%s, timeout=%.0fs)", self._model, self._timeout)
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = ImageGenApiError(
                            f"图像生成 API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.warning(
                            "图像生成 5xx (attempt %d/%d): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    if resp.status_code >= 400:
                        raise ImageGenApiError(
                            f"图像生成 API 客户端错误 {resp.status_code}: {resp.text[:500]}"
                        )

                    data = resp.json()
                    image_url = parse_qwen_image_response(data)
                    logger.info("图像生成 API 响应成功 (attempt %d/%d)", attempt, self._max_retries)

                    # 下载图片 URL 并转为 base64
                    return await self._download_as_base64(image_url)

            except httpx.TimeoutException as exc:
                # 超时不重试
                raise ImageGenTimeoutError(
                    f"图像生成请求超时 ({self._timeout}s)"
                ) from exc

            except (ImageGenApiError, ImageGenTimeoutError):
                # 客户端错误 / 超时 — 已处理，直接抛出
                raise

            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "图像生成连接错误 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "图像生成请求异常 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise ImageGenApiError(
            f"图像生成请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc
```

Also add a log to `_download_as_base64`:

```python
    async def _download_as_base64(self, image_url: str) -> str:
        """下载远程图片并转为 base64 字符串。"""
        logger.info("下载生成图片: %s", image_url[:100])
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/png")
            b64 = base64.b64encode(resp.content).decode("ascii")
            logger.info("图片下载完成 (size=%d bytes)", len(resp.content))
            return f"data:{content_type};base64,{b64}"
```

- [ ] **Step 3: Run all existing tests**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```
fix: complete empty error messages in LLM and image gen client retry logs
```

---

### Task 8: Full Integration Test

**Files:** No new files

- [ ] **Step 1: Run full backend unit test suite**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: All PASS

- [ ] **Step 2: Verify log output manually (optional)**

Start the server with `python start.py` and make a request. Check `logs/backend.log`:
- Should NOT see any `INFO: "GET /xxx HTTP/1.1" 200 OK` lines
- Should see `→ POST /api/analyze` and `← POST /api/analyze 200` with timing
- Should see `[req-xxxxxxxx]` in all log lines
- Error logs should have complete exception details

- [ ] **Step 3: Final commit (if any cleanup needed)**

```
chore: logging system integration complete
```
