"""Application Factory (create_app) 和 health endpoint 的单元测试。"""

from __future__ import annotations

import os
import json

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def env_vars(tmp_path, monkeypatch):
    """设置环境变量和临时目录，使 create_app() / 模块级 app 能正常初始化。"""
    comic_dir = tmp_path / "comics"
    history_file = tmp_path / "history.json"

    comic_dir.mkdir()
    history_file.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("COMIC_STORAGE_DIR", str(comic_dir))
    monkeypatch.setenv("HISTORY_FILE", str(history_file))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-placeholder")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    yield


@pytest.fixture
def app(env_vars):
    """通过 create_app() 创建干净的 FastAPI 实例。"""
    from app.main import create_app

    return create_app()


@pytest.fixture
def module_app(env_vars, monkeypatch):
    """获取模块级别的 app（包含 @app.get('/health') 注册的路由）。

    需要先清理可能的模块缓存，确保环境变量在导入前生效。
    """
    import importlib
    import app.main as main_module

    importlib.reload(main_module)
    return main_module.app


@pytest.fixture
def client(module_app):
    """同步 TestClient，基于模块级 app（包含所有路由）。"""
    return TestClient(module_app)


# ---------------------------------------------------------------------------
# test_returns_fastapi_instance
# ---------------------------------------------------------------------------


class TestCreateApp:
    """验证 create_app() 工厂函数。"""

    def test_returns_fastapi_instance(self, app) -> None:
        assert isinstance(app, FastAPI)


# ---------------------------------------------------------------------------
# test_health_endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """验证 GET /health 端点。"""

    def test_health_endpoint(self, client) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"status": "ok", "app": "SlangToon"}


# ---------------------------------------------------------------------------
# test_routers_registered
# ---------------------------------------------------------------------------


class TestRoutersRegistered:
    """验证所有路由已正确注册。"""

    def test_routers_registered(self, module_app) -> None:
        routes = [route.path for route in module_app.routes]
        assert "/api/generate-script" in routes
        assert "/api/generate-comic" in routes
        assert "/api/history" in routes
        assert "/health" in routes


# ---------------------------------------------------------------------------
# test_cors_middleware_present
# ---------------------------------------------------------------------------


class TestCORSMiddleware:
    """验证 CORS 中间件已配置。"""

    def test_cors_middleware_present(self, app) -> None:
        middleware_classes = [
            m.cls for m in app.user_middleware
        ]
        assert CORSMiddleware in middleware_classes


# ---------------------------------------------------------------------------
# test_logging_integration
# ---------------------------------------------------------------------------


class TestLoggingIntegration:
    """验证日志系统在 app 启动时正确初始化。"""

    def test_create_app_initializes_logging(self, app, tmp_path, monkeypatch):
        """create_app() 调用后，日志系统应已配置。"""
        import logging

        root = logging.getLogger()
        assert len(root.handlers) > 0

    def test_middleware_added(self, module_app, monkeypatch, tmp_path):
        """RequestIdMiddleware 应作为内部 middleware 注册。"""
        from app.middleware import RequestIdMiddleware

        found = False
        for mw in module_app.user_middleware:
            if mw.cls is not None and mw.cls.__name__ == "RequestIdMiddleware":
                found = True
                break
        assert found, "RequestIdMiddleware should be in user_middleware"
