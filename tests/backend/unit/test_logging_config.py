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
