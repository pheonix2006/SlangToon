# Logging System Design

**Date**: 2026-03-29
**Status**: Approved

## Problem

The current backend has no logging configuration. All logs use Python defaults + uvicorn defaults:

1. Uvicorn access logs flood the output with `INFO: "GET /xxx HTTP/1.1" 200 OK` — mostly noise
2. Application logs are minimal — only `logger.warning()` in retry paths of `llm_client.py` and `image_gen_client.py`
3. Error messages are incomplete — e.g., `LLM 请求超时 (attempt 2/3): ` with empty detail
4. Log formats are inconsistent — uvicorn uses `INFO:     ` prefix, app logs have no prefix
5. No request tracking — impossible to correlate logs from the same request under concurrency
6. No way to control log level without code changes

## Requirements

- Detailed request tracing with request_id and timing
- Output to file only (`logs/backend.log`), no terminal output
- Suppress uvicorn access logs entirely
- Complete error messages with exception details
- Environment variable `LOG_LEVEL` to control verbosity
- Unified log format across all modules

## Design

### 1. Logging Configuration Module (`backend/app/logging_config.py`, new)

Uses `logging.dictConfig()` for unified configuration.

**Unified format:**
```
[2026-03-29 14:30:15.123] [WARNING] [app.services.llm_client] [req-a3f1b2c4] LLM 请求超时 (attempt 2/3): ReadTimeout after 30s
```

Components: `[timestamp] [level] [module] [request_id] message`

- Timestamp: milliseconds precision
- Level: standard Python levels
- Module: `__name__` of the logger
- Request ID: injected via `contextvars`, empty string when no request context

**Key configuration:**
- `LOG_LEVEL` env var, default `INFO`
- Single `FileHandler` writing to `logs/backend.log`
- Force all third-party loggers (uvicorn, httpx, etc.) to `WARNING` level
- Request ID injected via custom `logging.Filter` reading from `contextvars`

### 2. Request ID Middleware (`backend/app/middleware.py`, new)

Lightweight ASGI middleware:
- Generates ID in format `req-{8-char-hex}` per request
- Stores ID in `contextvars.ContextVar`
- Logs request start (`→ METHOD /path`) and end (`← METHOD /path STATUS (耗时: Xs)`)
- Logs end as `WARNING` if response time > 1s or status >= 400

### 3. Disable Uvicorn Access Log

In `backend/run.py`, add `access_log=False` to `uvicorn.run()` and override `log_config` to prevent uvicorn from emitting any INFO-level logs.

### 4. Config Changes

`backend/app/config.py` — add field:
```python
log_level: str = "INFO"  # reads from LOG_LEVEL env var
```

`.env` and `.env.example` — add:
```
LOG_LEVEL=INFO
```

### 5. Log Points by Layer

**Routers (`backend/app/routers/`):**
- Entry point: log request received (path, method)
- Exit: log completion/failure (status, duration)
- Exception: log `ERROR` with full traceback context

**Services (`backend/app/services/`):**
- `llm_client.py`: log request start (model info), completion (duration), full error details on retry
- `image_gen_client.py`: log request start (style info), completion (duration), full error details on retry
- `analyze_service.py`: log LLM call start/end
- `generate_service.py`: log image generation start/end/save
- `history_service.py`: log query operations (count, pagination)

**Key improvement — complete error messages:**

Before:
```
LLM 请求超时 (attempt 2/3):
```

After:
```
LLM 请求超时 (attempt 2/3): httpx.ReadTimeout(read timeout of 30.0s)
```

### 6. Log Output Examples

**Normal request:**
```
[2026-03-29 14:30:15.123] [INFO]    [app.middleware]           [req-a3f1b2c4] → POST /api/analyze
[2026-03-29 14:30:15.456] [INFO]    [app.services.llm_client]  [req-a3f1b2c4] LLM 分析请求开始 (model=glm-4.6v)
[2026-03-29 14:30:18.789] [INFO]    [app.services.llm_client]  [req-a3f1b2c4] LLM 分析完成 (耗时: 3.3s)
[2026-03-29 14:30:18.790] [INFO]    [app.middleware]           [req-a3f1b2c4] ← POST /api/analyze 200 (耗时: 3.7s)
```

**Failed request:**
```
[2026-03-29 14:31:20.100] [INFO]    [app.middleware]                [req-d5e6f7a8] → POST /api/generate
[2026-03-29 14:31:20.102] [INFO]    [app.services.image_gen_client] [req-d5e6f7a8] 图片生成请求开始 (style=赛博朋克)
[2026-03-29 14:31:35.500] [WARNING] [app.services.image_gen_client] [req-d5e6f7a8] 图像生成 5xx (attempt 1/3): HTTPStatusError(500, body="rate limit exceeded")
[2026-03-29 14:31:50.800] [WARNING] [app.services.image_gen_client] [req-d5e6f7a8] 图像生成 5xx (attempt 2/3): HTTPStatusError(500, body="rate limit exceeded")
[2026-03-29 14:32:06.100] [WARNING] [app.services.image_gen_client] [req-d5e6f7a8] 图像生成 5xx (attempt 3/3): HTTPStatusError(500, body="rate limit exceeded")
[2026-03-29 14:32:06.101] [ERROR]   [app.routers.generate]         [req-d5e6f7a8] 图片生成失败: 所有重试已耗尽
[2026-03-29 14:32:06.101] [WARNING] [app.middleware]                [req-d5e6f7a8] ← POST /api/generate 500 (耗时: 46.0s)
```

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `backend/app/logging_config.py` | New | Logging configuration module |
| `backend/app/middleware.py` | New | Request ID middleware |
| `backend/app/config.py` | Modify | Add `log_level` field |
| `backend/app/main.py` | Modify | Mount middleware + init logging |
| `backend/run.py` | Modify | Disable uvicorn access log |
| `backend/app/routers/analyze.py` | Modify | Add log points |
| `backend/app/routers/generate.py` | Modify | Add log points |
| `backend/app/routers/history.py` | Modify | Add log points |
| `backend/app/services/analyze_service.py` | Modify | Add log points |
| `backend/app/services/generate_service.py` | Modify | Add log points |
| `backend/app/services/history_service.py` | Modify | Add log points |
| `backend/app/services/llm_client.py` | Modify | Complete error messages + add logs |
| `backend/app/services/image_gen_client.py` | Modify | Complete error messages + add logs |
| `.env` / `.env.example` | Modify | Add `LOG_LEVEL` |

**Not affected**: Frontend code, test code, storage module.
