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

        if elapsed > SLOW_REQUEST_THRESHOLD:
            logger.warning("← %s %s (耗时: %.1fs, 慢请求)", method, path, elapsed)
        else:
            logger.info("← %s %s (耗时: %.1fs)", method, path, elapsed)

    @staticmethod
    def _generate_request_id() -> str:
        """生成格式为 req-xxxxxxxx 的唯一请求 ID。"""
        return f"req-{uuid.uuid4().hex[:8]}"
