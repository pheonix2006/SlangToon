"""Request ID 中间件的单元测试。"""

import asyncio
import logging
import re

from unittest.mock import MagicMock

import pytest


class TestRequestIdMiddleware:
    """验证 RequestIdMiddleware 为每个请求分配唯一 ID 并记录日志。"""

    @pytest.fixture
    def log_file(self, tmp_path, monkeypatch):
        """配置日志输出到临时文件。"""
        log = tmp_path / "test.log"
        monkeypatch.setenv("PHOTO_STORAGE_DIR", str(tmp_path / "photos"))
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        from app.logging_config import setup_logging
        setup_logging(log_file=str(log), level="DEBUG")
        return log

    def test_assigns_request_id_format(self, log_file):
        """request_id 应为 req-xxxxxxxx 格式（8位hex）。"""
        from app.middleware import RequestIdMiddleware
        pattern = re.compile(r"^req-[0-9a-f]{8}$")
        for _ in range(20):
            rid = RequestIdMiddleware._generate_request_id()
            assert pattern.match(rid), f"Invalid request_id format: {rid}"

    def test_request_id_injected_to_context(self, log_file):
        """请求处理期间，request_id 应可通过 contextvars 获取。"""
        from app.middleware import RequestIdMiddleware
        from app.logging_config import request_id_ctx

        async def dummy_app(scope, receive, send):
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

    def test_logs_request_entry_and_exit(self, log_file):
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

        content = log_file.read_text(encoding="utf-8")
        assert "→ POST /api/analyze" in content
        assert "← POST /api/analyze" in content
