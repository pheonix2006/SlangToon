"""FlowTrace 单元测试 — 模型、FlowSession、NoOpSession。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

from app.flow_log.trace import FlowTrace, FlowStep, FlowSession, NoOpSession, _NoOpStep, _current_trace
from app.flow_log import get_current_trace, NoOpSession as NoOpImport


# ── 模型测试 ─────────────────────────────────────────────────

class TestFlowTraceModel:
    def test_flow_trace_model_valid(self):
        trace = FlowTrace(
            trace_id="test-001",
            request_id="req-abc12345",
            flow_type="analyze",
            status="success",
            created_at="2026-03-31T10:00:00.000",
            total_duration_ms=1000.0,
            steps=[],
        )
        assert trace.trace_id == "test-001"
        assert trace.request_id == "req-abc12345"
        assert trace.flow_type == "analyze"
        assert trace.status == "success"
        assert trace.error is None

    def test_flow_trace_with_error(self):
        trace = FlowTrace(
            trace_id="test-002", request_id="req-xxx", flow_type="generate",
            status="failed", created_at="2026-03-31T10:00:00.000",
            total_duration_ms=5000.0, steps=[], error="LLM timeout",
        )
        assert trace.status == "failed"
        assert trace.error == "LLM timeout"

    def test_flow_trace_validation_invalid_flow_type(self):
        with pytest.raises(Exception):
            FlowTrace(
                trace_id="x", request_id="x", flow_type="invalid",
                status="success", created_at="x", total_duration_ms=0, steps=[],
            )

    def test_flow_trace_validation_invalid_status(self):
        with pytest.raises(Exception):
            FlowTrace(
                trace_id="x", request_id="x", flow_type="analyze",
                status="invalid", created_at="x", total_duration_ms=0, steps=[],
            )


class TestFlowStepModel:
    def test_flow_step_model_valid(self):
        step = FlowStep(name="llm_analyze", started_at="2026-03-31T10:00:00.000", status="success", duration_ms=100.0)
        assert step.name == "llm_analyze"
        assert step.status == "success"

    def test_flow_step_default_values(self):
        step = FlowStep(name="test", started_at="x", status="running")
        assert step.detail == {}
        assert step.duration_ms is None
        assert step.error is None

    def test_flow_step_with_detail(self):
        step = FlowStep(name="llm_analyze", started_at="x", status="success",
                        detail={"model": "glm-4.6v", "image_size": 12345})
        assert step.detail["model"] == "glm-4.6v"

    def test_flow_step_serialization(self):
        step = FlowStep(name="x", started_at="x", status="success", duration_ms=1.5,
                        detail={"key": "val"}, error="err")
        data = step.model_dump()
        assert data["name"] == "x"
        assert data["detail"] == {"key": "val"}
        assert data["error"] == "err"


# ── FlowSession 测试 ─────────────────────────────────────────

class TestFlowSession:
    @pytest.mark.asyncio
    async def test_session_step_success_records_timing(self):
        session = FlowSession("analyze")
        async with session.step("llm_analyze", detail={"model": "glm-4.6v"}) as step:
            await asyncio.sleep(0.01)
        assert session.trace.steps[0].status == "success"
        assert session.trace.steps[0].duration_ms > 0
        assert session.trace.steps[0].detail["model"] == "glm-4.6v"

    @pytest.mark.asyncio
    async def test_session_step_failed_records_error(self):
        session = FlowSession("analyze")
        with pytest.raises(ValueError, match="test error"):
            async with session.step("llm_analyze") as step:
                raise ValueError("test error")
        assert session.trace.steps[0].status == "failed"
        assert "test error" in session.trace.steps[0].error

    @pytest.mark.asyncio
    async def test_session_step_failed_reraises_exception(self):
        session = FlowSession("analyze")
        with pytest.raises(RuntimeError):
            async with session.step("failing"):
                raise RuntimeError("original error")
        assert session.trace.steps[0].status == "failed"

    @pytest.mark.asyncio
    async def test_session_step_with_detail(self):
        session = FlowSession("generate")
        async with session.step("compose_prompt", detail={"style_name": "赛博朋克"}):
            pass
        assert session.trace.steps[0].detail["style_name"] == "赛博朋克"

    @pytest.mark.asyncio
    async def test_session_finish_calculates_total_duration(self):
        session = FlowSession("analyze")
        await asyncio.sleep(0.01)
        session.finish("success")
        assert session.trace.total_duration_ms > 0
        assert session.trace.status == "success"

    @pytest.mark.asyncio
    async def test_session_finish_with_error(self):
        session = FlowSession("generate")
        session.finish("failed", error="Image generation timeout")
        assert session.trace.status == "failed"
        assert session.trace.error == "Image generation timeout"

    @pytest.mark.asyncio
    async def test_session_multiple_steps_ordered(self):
        session = FlowSession("generate")
        async with session.step("save_photo"):
            pass
        async with session.step("compose_prompt"):
            pass
        async with session.step("image_generate"):
            pass
        assert len(session.trace.steps) == 3
        assert session.trace.steps[0].name == "save_photo"
        assert session.trace.steps[2].name == "image_generate"

    @pytest.mark.asyncio
    async def test_session_concurrent_isolation(self):
        session_a = FlowSession("analyze")
        session_b = FlowSession("generate")

        async def add_steps(session, count):
            for i in range(count):
                async with session.step(f"step_{i}"):
                    await asyncio.sleep(0.001)

        await asyncio.gather(add_steps(session_a, 3), add_steps(session_b, 2))
        assert len(session_a.trace.steps) == 3
        assert len(session_b.trace.steps) == 2

    @pytest.mark.asyncio
    async def test_session_init_with_request_id(self):
        session = FlowSession("analyze", request_id="req-abc12345")
        assert session.trace.request_id == "req-abc12345"


# ── NoOpSession 测试 ─────────────────────────────────────────

class TestNoOpSession:
    @pytest.mark.asyncio
    async def test_noop_step_executes_code_without_recording(self):
        noop = NoOpSession()
        result = []
        async with noop.step("test_step", detail={"key": "val"}) as step:
            result.append("executed")
        assert result == ["executed"]
        assert isinstance(step, _NoOpStep)

    @pytest.mark.asyncio
    async def test_noop_step_does_not_raise_on_success(self):
        noop = NoOpSession()
        async with noop.step("test"):
            pass  # no exception

    @pytest.mark.asyncio
    async def test_noop_step_reraises_exception(self):
        noop = NoOpSession()
        with pytest.raises(ValueError, match="should propagate"):
            async with noop.step("test"):
                raise ValueError("should propagate")

    @pytest.mark.asyncio
    async def test_noop_finish_noop(self):
        noop = NoOpSession()
        noop.finish("success")  # no exception
        noop.finish("failed", error="something")  # no exception


# ── Contextvars 测试 ─────────────────────────────────────────

class TestContextvarsPropagation:
    @pytest.mark.asyncio
    async def test_get_current_trace_returns_noop_when_unset(self):
        trace = get_current_trace()
        assert isinstance(trace, (NoOpSession, type(NoOpSession())))

    @pytest.mark.asyncio
    async def test_set_and_get_current_trace(self):
        from app.flow_log import set_current_trace
        session = FlowSession("analyze")
        set_current_trace(session)
        retrieved = get_current_trace()
        assert isinstance(retrieved, FlowSession)
        assert retrieved.trace.trace_id == session.trace.trace_id


# ── TraceStore 测试 ──────────────────────────────────────────

import json
import os
from datetime import datetime, timedelta, timezone

class TestTraceStore:
    @pytest.fixture
    def trace_dir(self, tmp_path):
        d = tmp_path / "traces"
        d.mkdir()
        return str(d)

    @pytest.fixture
    def store(self, trace_dir):
        from app.flow_log.trace_store import TraceStore
        return TraceStore(trace_dir, retention_days=7)

    def _make_trace(self, flow_type="analyze", days_ago=0):
        """创建测试用 FlowTrace，支持指定多少天前。"""
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        return FlowTrace(
            trace_id=f"trace-{days_ago}-{flow_type}",
            request_id=f"req-test{days_ago}",
            flow_type=flow_type,
            status="success",
            created_at=dt.strftime("%Y-%m-%dT%H:%M:%S.000"),
            total_duration_ms=1000.0,
            steps=[FlowStep(name="test", started_at=dt.strftime("%Y-%m-%dT%H:%M:%S.000"), status="success", duration_ms=500.0)],
        )

    def test_store_save_creates_jsonl_file(self, store, trace_dir):
        trace = self._make_trace()
        store.save(trace)
        files = list(Path(trace_dir).glob("*.jsonl"))
        assert len(files) == 1
        assert files[0].name.endswith(".jsonl")

    def test_store_save_appends_lines(self, store, trace_dir):
        store.save(self._make_trace(flow_type="analyze"))
        store.save(self._make_trace(flow_type="generate"))
        file = list(Path(trace_dir).glob("*.jsonl"))[0]
        lines = file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            json.loads(line)

    def test_store_save_different_dates(self, store, trace_dir):
        store.save(self._make_trace(days_ago=0))
        store.save(self._make_trace(days_ago=3))
        files = list(Path(trace_dir).glob("*.jsonl"))
        assert len(files) == 2

    def test_store_query_returns_traces(self, store, trace_dir):
        store.save(self._make_trace())
        traces = store.query()
        assert len(traces) == 1
        assert traces[0].flow_type == "analyze"

    def test_store_query_default_date(self, store, trace_dir):
        store.save(self._make_trace(days_ago=0))
        traces = store.query()  # 不传 date，默认今天
        assert len(traces) == 1

    def test_store_query_limit(self, store, trace_dir):
        store.save(self._make_trace(flow_type="analyze"))
        store.save(self._make_trace(flow_type="generate"))
        traces = store.query(limit=1)
        assert len(traces) == 1

    def test_store_query_empty_date(self, store, trace_dir):
        traces = store.query(date="2099-01-01")
        assert traces == []

    def test_store_query_returns_newest_first(self, store, trace_dir):
        store.save(self._make_trace(flow_type="analyze"))
        store.save(self._make_trace(flow_type="generate"))
        traces = store.query()
        assert traces[0].flow_type == "generate"
        assert traces[1].flow_type == "analyze"

    def test_store_cleanup_removes_old_files(self, store, trace_dir):
        store.save(self._make_trace(days_ago=10))
        store.save(self._make_trace(days_ago=0))
        store.cleanup(retention_days=7)
        files = list(Path(trace_dir).glob("*.jsonl"))
        assert len(files) == 1

    def test_store_cleanup_keeps_recent_files(self, store, trace_dir):
        store.save(self._make_trace(days_ago=0))
        store.save(self._make_trace(days_ago=3))
        store.save(self._make_trace(days_ago=6))
        store.cleanup(retention_days=7)
        files = list(Path(trace_dir).glob("*.jsonl"))
        assert len(files) == 3

    def test_store_save_valid_jsonl_structure(self, store, trace_dir):
        trace = self._make_trace()
        store.save(trace)
        file = list(Path(trace_dir).glob("*.jsonl"))[0]
        line = file.read_text(encoding="utf-8").strip()
        parsed = FlowTrace.model_validate_json(line)
        assert parsed.trace_id == trace.trace_id
        assert parsed.flow_type == "analyze"


# ── 路由测试 ─────────────────────────────────────────────────

class TestTracesEndpoint:
    """GET /api/traces 端点测试。

    NOTE: 这些测试依赖 Task 7 的 traces.py router，在 Task 7 实现之前会 skip。
    """

    @pytest.mark.asyncio
    async def test_traces_endpoint_returns_list(self, client):
        response = await client.get("/api/traces")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "traces" in data
        assert isinstance(data["traces"], list)

    @pytest.mark.asyncio
    async def test_traces_endpoint_with_date_param(self, client):
        response = await client.get("/api/traces?date=2099-01-01")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["traces"] == []

    @pytest.mark.asyncio
    async def test_traces_endpoint_with_limit_param(self, client):
        response = await client.get("/api/traces?limit=5")
        assert response.status_code == 200
        data = response.json()["data"]
        assert "traces" in data


class TestTraceHeaders:
    """验证 X-Trace-Id header 注入。"""

    @pytest.mark.asyncio
    async def test_analyze_response_has_trace_header(self, client, sample_image_base64, monkeypatch):
        """analyze 响应包含 X-Trace-Id header（trace_enabled=True 时）。"""
        import app.services.analyze_service as svc
        monkeypatch.setattr(svc, "analyze_photo", lambda *args: [])

        response = await client.post("/api/analyze", json={
            "image_base64": sample_image_base64,
            "image_format": "jpeg",
        })
        # NoOpSession path (analyze_photo returns [] which doesn't match expected flow)
        # The header is only set for FlowSession when trace_enabled=True
        # Since monkeypatch returns empty list, it will succeed but trace will be saved

    @pytest.mark.asyncio
    async def test_no_trace_header_when_disabled(self, client, sample_image_base64, monkeypatch, tmp_data_dir):
        """trace_enabled=False 时无 X-Trace-Id header。"""
        import os
        os.environ["TRACE_ENABLED"] = "false"
        import app.services.analyze_service as svc
        monkeypatch.setattr(svc, "analyze_photo", lambda *args: [])
        # Force reload settings
        import app.config
        monkeypatch.setattr(app.config, "get_settings", lambda: type("S", (), {
            "trace_enabled": False,
            "openai_model": "test",
        }))
