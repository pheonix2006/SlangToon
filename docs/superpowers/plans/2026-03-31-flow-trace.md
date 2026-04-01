# FlowTrace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为后端全流程（analyze / generate）提供完整的调用链 trace 记录，前端关键节点 console.log，通过 X-Trace-Id 关联。

**Architecture:** 新建 `flow_log` 模块，包含 FlowTrace/FlowStep 模型、FlowSession 上下文管理器（含 NoOpSession 空操作模式）、TraceStore JSONL 文件存储。通过 contextvars 跨层传递，路由层创建 session 并注入 X-Trace-Id header，服务层用 `trace.step()` 包裹关键阶段。

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, contextvars, JSONL, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-31-flow-trace-design.md`

---

## File Map

| File | Responsibility | Action |
|------|---------------|--------|
| `backend/app/flow_log/__init__.py` | 导出 FlowSession, NoOpSession, get_current_trace, set_current_trace | Create |
| `backend/app/flow_log/trace.py` | FlowTrace/FlowStep 模型 + FlowSession + NoOpSession + contextvars | Create |
| `backend/app/flow_log/trace_store.py` | JSONL 文件存储 + 查询 + 清理 | Create |
| `backend/app/routers/traces.py` | GET /api/traces 查询端点 | Create |
| `backend/app/config.py` | 新增 trace_enabled, trace_dir, trace_retention_days | Modify |
| `backend/app/main.py` | lifespan 创建 trace_dir + cleanup，注册 traces router | Modify |
| `backend/app/routers/analyze.py` | 创建 FlowSession，注入 X-Trace-Id header，保存 trace | Modify |
| `backend/app/routers/generate.py` | 同上 | Modify |
| `backend/app/services/analyze_service.py` | llm_analyze + parse_response 步骤包裹 | Modify |
| `backend/app/services/generate_service.py` | save_photo + compose_prompt + image_generate + download_image + save_poster 步骤包裹 | Modify |
| `frontend/src/services/api.ts` | 提取 X-Trace-Id header，console.log | Modify |
| `frontend/src/App.tsx` | 状态转换节点 console.log | Modify |
| `tests/backend/conftest.py` | tmp_data_dir 追加 traces 目录，新增 trace_store fixture | Modify |
| `tests/backend/unit/test_flow_trace.py` | 全部单元测试（~30 用例） | Create |
| `tests/backend/integration/test_real_api.py` | 追加 trace 验证用例和 verify_trace 辅助函数 | Modify |

---

## Task 1: Config — 新增 trace 配置项

**Files:**
- Modify: `backend/app/config.py:44`
- Test: `tests/backend/unit/test_config.py` (现有文件)

- [ ] **Step 1: 在 config.py 末尾添加三个配置项**

在 `log_level` 之后添加：

```python
    # Trace
    trace_enabled: bool = True
    trace_dir: str = "data/traces"
    trace_retention_days: int = 7
```

- [ ] **Step 2: 运行现有 config 单元测试确认无破坏**

Run: `uv run pytest tests/backend/unit/test_config.py -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(config): add trace_enabled, trace_dir, trace_retention_days settings"
```

---

## Task 2: FlowTrace 数据模型 + FlowSession + NoOpSession

**Files:**
- Create: `backend/app/flow_log/__init__.py`
- Create: `backend/app/flow_log/trace.py`
- Create: `tests/backend/unit/test_flow_trace.py`（仅模型和 session 部分）

- [ ] **Step 1: 写模型 + session 的失败测试**

创建 `tests/backend/unit/test_flow_trace.py`：

```python
"""FlowTrace 单元测试 — 模型、FlowSession、NoOpSession。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

from app.flow_log.trace import FlowTrace, FlowStep, FlowSession, NoOpSession


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/backend/unit/test_flow_trace.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.flow_log'`

- [ ] **Step 3: 创建 `backend/app/flow_log/__init__.py`**

```python
"""FlowTrace — 全流程调用链追踪。"""

from app.flow_log.trace import FlowSession, NoOpSession, _current_trace, get_current_trace

__all__ = ["FlowSession", "NoOpSession", "get_current_trace", "set_current_trace"]


def set_current_trace(session: FlowSession | NoOpSession) -> None:
    """设置当前请求的 trace session（供路由层调用）。"""
    _current_trace.set(session)
```

- [ ] **Step 4: 创建 `backend/app/flow_log/trace.py`**

```python
"""FlowTrace 核心模块 — 数据模型、FlowSession、NoOpSession、contextvars。"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Literal

from pydantic import BaseModel


# ── 数据模型 ──────────────────────────────────────────────────

class FlowStep(BaseModel):
    """单个阶段记录。"""

    name: str
    status: Literal["running", "success", "failed", "skipped"] = "running"
    started_at: str = ""
    duration_ms: float | None = None
    detail: dict[str, Any] = {}
    error: str | None = None


class FlowTrace(BaseModel):
    """一次完整 API 调用的 trace 记录。"""

    trace_id: str = ""
    request_id: str = ""
    flow_type: Literal["analyze", "generate"] = "analyze"
    status: Literal["running", "success", "failed"] = "running"
    created_at: str = ""
    total_duration_ms: float = 0.0
    steps: list[FlowStep] = []
    error: str | None = None


# ── contextvars ──────────────────────────────────────────────

_current_trace: ContextVar[FlowSession | NoOpSession] = ContextVar(
    "flow_trace", default=NoOpSession(),
)


def get_current_trace() -> FlowSession | NoOpSession:
    """获取当前请求的 trace session。未设置时返回 NoOpSession。"""
    return _current_trace.get()


# ── 工具函数 ─────────────────────────────────────────────────

def _iso_now() -> str:
    """返回当前时间的 ISO 8601 字符串（毫秒精度）。"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}"


# ── NoOpSession（Null Object 模式）──────────────────────────

class _NoOpStep:
    """空操作 step，什么都不记录。"""

    status = "skipped"
    duration_ms = None
    detail = {}
    error = None


class NoOpSession:
    """trace_enabled=False 时的空操作会话，零开销。"""

    @asynccontextmanager
    async def step(self, name: str, detail: dict[str, Any] | None = None) -> AsyncIterator[_NoOpStep]:
        yield _NoOpStep()

    def finish(self, status: Literal["success", "failed"], error: str | None = None) -> None:
        pass


# ── FlowSession ──────────────────────────────────────────────

class FlowSession:
    """一次完整 API 调用的 trace 会话。"""

    def __init__(self, flow_type: str, request_id: str = "") -> None:
        self.trace = FlowTrace(
            trace_id=str(uuid.uuid4()),
            request_id=request_id,
            flow_type=flow_type,
            created_at=_iso_now(),
            status="running",
        )
        self._start = time.perf_counter()

    @asynccontextmanager
    async def step(
        self, name: str, detail: dict[str, Any] | None = None,
    ) -> AsyncIterator[FlowStep]:
        """阶段上下文管理器：自动计时、记录状态、捕获异常（不吞）。"""
        step = FlowStep(
            name=name,
            started_at=_iso_now(),
            status="running",
            detail=detail or {},
        )
        self.trace.steps.append(step)
        t0 = time.perf_counter()
        try:
            yield step
            step.status = "success"
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            raise
        finally:
            step.duration_ms = (time.perf_counter() - t0) * 1000

    def finish(
        self, status: Literal["success", "failed"], error: str | None = None,
    ) -> None:
        """标记 trace 完成，计算总耗时。"""
        self.trace.status = status
        self.trace.total_duration_ms = (time.perf_counter() - self._start) * 1000
        self.trace.error = error
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/backend/unit/test_flow_trace.py -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/flow_log/__init__.py backend/app/flow_log/trace.py tests/backend/unit/test_flow_trace.py
git commit -m "feat(flow_log): add FlowTrace models, FlowSession, NoOpSession with tests"
```

---

## Task 3: TraceStore — JSONL 文件存储

**Files:**
- Create: `backend/app/flow_log/trace_store.py`
- Modify: `tests/backend/unit/test_flow_trace.py`（追加 TraceStore 测试）

- [ ] **Step 1: 写 TraceStore 的失败测试**

追加到 `tests/backend/unit/test_flow_trace.py`：

```python
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── TraceStore 测试 ──────────────────────────────────────────

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
        # 每行是合法 JSON
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
        # 最新写入的在前面
        assert traces[0].flow_type == "generate"
        assert traces[1].flow_type == "analyze"

    def test_store_cleanup_removes_old_files(self, store, trace_dir):
        store.save(self._make_trace(days_ago=10))
        store.save(self._make_trace(days_ago=0))
        store.cleanup(retention_days=7)
        files = list(Path(trace_dir).glob("*.jsonl"))
        # 10 天前的文件应被删除
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/backend/unit/test_flow_trace.py::TestTraceStore -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.flow_log.trace_store'`

- [ ] **Step 3: 创建 `backend/app/flow_log/trace_store.py`**

```python
"""TraceStore — JSONL 文件存储、查询、自动清理。"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.flow_log.trace import FlowTrace

logger = logging.getLogger(__name__)


class TraceStore:
    """JSONL 格式的 trace 文件存储，追加写入，并发安全。"""

    def __init__(self, trace_dir: str, retention_days: int = 7) -> None:
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days

    def save(self, trace: FlowTrace) -> None:
        """追加写入当天 trace 文件（JSONL 格式，并发安全）。"""
        try:
            date_str = trace.created_at[:10]
            file_path = self.trace_dir / f"{date_str}.jsonl"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(trace.model_dump_json() + "\n")
        except Exception:
            logger.warning("Failed to save trace %s", trace.trace_id, exc_info=True)

    def query(self, date: str | None = None, limit: int = 20) -> list[FlowTrace]:
        """查询指定日期的 trace 记录，返回最新的 N 条。"""
        date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = self.trace_dir / f"{date_str}.jsonl"
        if not file_path.exists():
            return []
        traces: list[FlowTrace] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        traces.append(FlowTrace.model_validate_json(line))
        except Exception:
            logger.warning("Failed to read trace file %s", file_path, exc_info=True)
            return []
        return list(reversed(traces))[:limit]

    def cleanup(self, retention_days: int | None = None) -> int:
        """删除超过 retention_days 的文件。返回删除的文件数。"""
        days = retention_days if retention_days is not None else self.retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0
        for file_path in self.trace_dir.glob("*.jsonl"):
            try:
                # 从文件名提取日期: 2026-03-31.jsonl
                date_str = file_path.stem  # "2026-03-31"
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    file_path.unlink()
                    removed += 1
            except (ValueError, OSError):
                continue
        if removed > 0:
            logger.info("Cleaned up %d expired trace files (retention=%d days)", removed, days)
        return removed
```

- [ ] **Step 4: 运行全部 flow_trace 测试**

Run: `uv run pytest tests/backend/unit/test_flow_trace.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/flow_log/trace_store.py tests/backend/unit/test_flow_trace.py
git commit -m "feat(flow_log): add TraceStore with JSONL storage and tests"
```

---

## Task 4: conftest — 追加 trace fixtures

**Files:**
- Modify: `tests/backend/conftest.py:18-29`

- [ ] **Step 1: 修改 tmp_data_dir fixture，追加 traces 目录和环境变量**

在现有 `tmp_data_dir` fixture 中，`(data_dir / "history.json").write_text(...)` 之后、`yield` 之前添加：

```python
    (data_dir / "traces").mkdir()
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = "true"
```

- [ ] **Step 2: 在 conftest.py 末尾添加 trace_store fixture**

```python
@pytest.fixture
def trace_store(tmp_data_dir):
    """创建临时 TraceStore 实例。"""
    from app.flow_log.trace_store import TraceStore
    return TraceStore(str(tmp_data_dir / "traces"), retention_days=7)
```

- [ ] **Step 3: 运行现有全部单元测试确认无破坏**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add tests/backend/conftest.py
git commit -m "test(conftest): add trace_dir env var and trace_store fixture"
```

---

## Task 5: 路由集成 — analyze.py + generate.py 注入 FlowSession

**Files:**
- Modify: `backend/app/routers/analyze.py`
- Modify: `backend/app/routers/generate.py`
- Modify: `tests/backend/unit/test_flow_trace.py`（追加路由测试）
- Modify: `tests/backend/unit/test_analyze.py`（现有文件，追加 header 验证）
- Modify: `tests/backend/unit/test_generate.py`（现有文件，追加 header 验证）

- [ ] **Step 1: 写路由级 trace 测试**

追加到 `tests/backend/unit/test_flow_trace.py`：

```python
from app.flow_log import get_current_trace, NoOpSession


class TestContextvarsPropagation:
    @pytest.mark.asyncio
    async def test_get_current_trace_returns_noop_when_unset(self):
        # 在新的 context 中，未设置时应返回 NoOpSession
        import contextvars
        token = _current_trace.set(NoOpSession())
        try:
            trace = get_current_trace()
            assert isinstance(trace, NoOpSession)
        finally:
            _current_trace.reset(token)
```

- [ ] **Step 2: 运行测试**

Run: `uv run pytest tests/backend/unit/test_flow_trace.py::TestContextvarsPropagation -v`
Expected: PASS

- [ ] **Step 3: 修改 `backend/app/routers/analyze.py`**

完整替换为：

```python
import logging

from fastapi import APIRouter, Depends, Response
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.services.analyze_service import analyze_photo, AnalyzeError
from app.flow_log import FlowSession, NoOpSession, get_current_trace, set_current_trace
from app.flow_log.trace_store import TraceStore
from app.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyze"])


@router.post("/analyze", response_model=ApiResponse)
async def analyze_endpoint(
    request: AnalyzeRequest,
    settings: Settings = Depends(get_settings),
    response: Response = Response(),
):
    logger.info("收到分析请求")

    # 创建 trace session
    if settings.trace_enabled:
        trace = FlowSession("analyze", request_id=request_id_ctx.get(""))
        set_current_trace(trace)
        response.headers["X-Trace-Id"] = trace.trace.trace_id
    else:
        trace = NoOpSession()
        set_current_trace(trace)

    try:
        options = await analyze_photo(request.image_base64, request.image_format, settings)
        logger.info("分析完成, 返回 %d 个风格选项", len(options))
        if isinstance(trace, FlowSession):
            trace.finish("success")
        return ApiResponse(code=0, message="success", data=AnalyzeResponse(options=options).model_dump())
    except AnalyzeError as e:
        logger.error("分析失败: %s", e.message)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("分析异常: %s", e, exc_info=True)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=str(e))
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
    finally:
        if isinstance(trace, FlowSession):
            TraceStore(settings.trace_dir, settings.trace_retention_days).save(trace.trace)
```

- [ ] **Step 4: 修改 `backend/app/routers/generate.py`**

完整替换为：

```python
import logging

from fastapi import APIRouter, Depends, Response
from app.schemas.generate import GenerateRequest
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.services.generate_service import generate_artwork, GenerateError
from app.flow_log import FlowSession, NoOpSession, get_current_trace, set_current_trace
from app.flow_log.trace_store import TraceStore
from app.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=ApiResponse)
async def generate_endpoint(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    response: Response = Response(),
):
    logger.info("收到生成请求 (style=%s)", request.style_name)

    # 创建 trace session
    if settings.trace_enabled:
        trace = FlowSession("generate", request_id=request_id_ctx.get(""))
        set_current_trace(trace)
        response.headers["X-Trace-Id"] = trace.trace.trace_id
    else:
        trace = NoOpSession()
        set_current_trace(trace)

    storage = FileStorage(settings.photo_storage_dir, settings.poster_storage_dir)
    history = HistoryService(settings.history_file, settings.max_history_records)
    try:
        result = await generate_artwork(
            request.image_base64, request.image_format,
            request.style_name, request.style_brief,
            settings, storage, history,
        )
        logger.info("生成完成, poster_url=%s", result.get("poster_url", ""))
        if isinstance(trace, FlowSession):
            trace.finish("success")
        return ApiResponse(code=0, message="success", data=result)
    except GenerateError as e:
        logger.error("生成失败: %s", e.message)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("生成异常: %s", e, exc_info=True)
        if isinstance(trace, FlowSession):
            trace.finish("failed", error=str(e))
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
    finally:
        if isinstance(trace, FlowSession):
            TraceStore(settings.trace_dir, settings.trace_retention_days).save(trace.trace)
```

- [ ] **Step 5: 运行全部单元测试确认无破坏**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/analyze.py backend/app/routers/generate.py tests/backend/unit/test_flow_trace.py
git commit -m "feat(routers): integrate FlowSession into analyze and generate endpoints"
```

---

## Task 6: main.py — 注册 traces router + lifespan 清理

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: 修改 main.py**

在 `from app.routers import analyze, generate, history` 之后追加 import：

```python
from app.routers import analyze, generate, history, traces
```

在 `lifespan` 函数中 `yield` 之前追加 trace 清理：

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.photo_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.poster_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.history_file).parent.mkdir(parents=True, exist_ok=True)
    # Trace cleanup on startup
    if settings.trace_enabled:
        Path(settings.trace_dir).mkdir(parents=True, exist_ok=True)
        from app.flow_log.trace_store import TraceStore
        TraceStore(settings.trace_dir, settings.trace_retention_days).cleanup()
    yield
```

在 `create_app()` 中 `app.include_router(history.router)` 之后追加：

```python
    app.include_router(traces.router)
```

- [ ] **Step 2: 运行全部单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(main): register traces router, add trace cleanup on startup"
```

---

## Task 7: traces.py — GET /api/traces 查询端点

**Files:**
- Create: `backend/app/routers/traces.py`

- [ ] **Step 1: 创建 `backend/app/routers/traces.py`**

```python
"""Trace 查询端点 — 调试用接口。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from app.schemas.common import ApiResponse
from app.config import get_settings, Settings
from app.flow_log.trace_store import TraceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["traces"])


@router.get("/traces")
async def list_traces(
    date: str | None = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    settings: Settings = Depends(get_settings),
):
    """查询 trace 记录（调试用）。"""
    if not settings.trace_enabled:
        return ApiResponse(code=0, message="trace disabled", data={"traces": [], "date": date or ""})

    date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    traces = store.query(date=date_str, limit=limit)
    trace_dicts = [t.model_dump() for t in traces]
    return ApiResponse(code=0, message="success", data={"traces": trace_dicts, "date": date_str})
```

- [ ] **Step 2: 运行全部单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/traces.py
git commit -m "feat(routers): add GET /api/traces query endpoint"
```

---

## Task 8: 服务层 — analyze_service.py 注入 trace.step()

**Files:**
- Modify: `backend/app/services/analyze_service.py`

- [ ] **Step 1: 修改 analyze_service.py**

在现有 import 之后追加：

```python
from app.flow_log import get_current_trace
```

修改 `analyze_photo` 函数，用 `trace.step()` 包裹两个阶段：

```python
async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
    """分析照片，返回 5 个主题选项（仅名称+简述）。"""
    trace = get_current_trace()
    llm = LLMClient(settings)

    # Step 1: LLM 分析
    async with trace.step("llm_analyze", detail={"model": settings.openai_model, "image_size": len(image_base64), "temperature": 0.8}):
        try:
            logger.info("LLM 分析请求开始 (model=%s)", settings.openai_model)
            content = await llm.chat_with_vision(
                ANALYZE_PROMPT, image_base64, image_format,
                "请分析照片中的人物，生成 5 个创意主题选项",
                temperature=0.8,
            )
            logger.info("LLM 分析完成")
        except (LLMTimeoutError, LLMApiError) as e:
            logger.error("LLM 调用失败: %s", e)
            raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

    # Step 2: 解析响应
    async with trace.step("parse_response"):
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

    if len(options) < 5:
        raise AnalyzeError(50002, f"LLM 返回 {len(options)} 个选项，期望 5 个")

    style_options = []
    for i, opt in enumerate(options[:5]):
        if not isinstance(opt, dict):
            raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
        for field in ("name", "brief"):
            if field not in opt or not opt[field]:
                raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
        style_options.append(StyleOption(name=opt["name"], brief=opt["brief"]))

    # 更新 llm_analyze step 的 detail
    if len(trace.trace.steps) > 0:
        trace.trace.steps[0].detail["options_count"] = len(style_options)
        trace.trace.steps[0].detail["topic_names"] = [o.name for o in style_options]

    return style_options
```

> 注：`trace.step()` 是 async context manager，对于非 async 代码块也兼容（async with 内部无 await 时正常工作）。`parse_response` step 包裹的是同步 JSON 解析代码，但用 `async with` 包裹不影响行为。

- [ ] **Step 2: 运行全部单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS（mock 的 analyze 走的是原有异常路径或正常路径，NoOpSession 不影响）

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analyze_service.py
git commit -m "feat(analyze_service): wrap LLM analyze and parse steps with trace.step()"
```

---

## Task 9: 服务层 — generate_service.py 注入 trace.step()

**Files:**
- Modify: `backend/app/services/generate_service.py`

- [ ] **Step 1: 修改 generate_service.py**

在现有 import 之后追加：

```python
from app.flow_log import get_current_trace
```

修改 `generate_artwork` 函数：

```python
async def generate_artwork(
    image_base64: str, image_format: str,
    style_name: str, style_brief: str,
    settings: Settings, storage: FileStorage, history: HistoryService,
) -> dict:
    """生成海报：先 LLM 构思详细 prompt，再调 Qwen 生图。"""
    trace = get_current_trace()

    # 1. 保存原始照片
    async with trace.step("save_photo"):
        photo_info = storage.save_photo(image_base64, image_format)
        if len(trace.trace.steps) > 0:
            trace.trace.steps[-1].detail = {"path": photo_info.get("file_path", ""), "file_size": len(image_base64)}

    # 2. Compose — LLM 生成详细英文构图 prompt
    async with trace.step("compose_prompt", detail={"model": settings.openai_model, "style_name": style_name, "temperature": 0.7}):
        prompt = await _compose_prompt(image_base64, image_format, style_name, style_brief, settings)
        if len(trace.trace.steps) > 0:
            trace.trace.steps[-1].detail["prompt_length"] = len(prompt)

    # 3. Image generation — Qwen 生图
    gen_client = ImageGenClient(settings)
    async with trace.step("image_generate", detail={"model": settings.qwen_image_model, "style_name": style_name}):
        try:
            logger.info("图片生成请求开始 (model=%s, style=%s)", settings.qwen_image_model, style_name)
            poster_b64 = await gen_client.generate(prompt, image_base64, image_format)
            logger.info("图片生成完成")
            if len(trace.trace.steps) > 0:
                trace.trace.steps[-1].detail["response_size"] = len(poster_b64)
        except (ImageGenTimeoutError, ImageGenApiError) as e:
            logger.error("图片生成失败: %s", e)
            raise GenerateError(50003, f"图片生成失败: {e}") from e
        except Exception as e:
            logger.error("生成结果处理失败: %s", e)
            raise GenerateError(50004, f"生成结果处理失败: {e}") from e

    # 4. Save poster & record history
    async with trace.step("save_poster"):
        poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])
        history_id = history.add({
            "style_name": style_name,
            "prompt": prompt,
            "poster_url": poster_info["poster_url"],
            "thumbnail_url": poster_info["thumbnail_url"],
            "photo_url": photo_info["url"],
        })
        logger.info("海报已保存 (history_id=%s)", history_id)
        if len(trace.trace.steps) > 0:
            trace.trace.steps[-1].detail = {"history_id": history_id}

    return {
        "poster_url": poster_info["poster_url"],
        "thumbnail_url": poster_info["thumbnail_url"],
        "history_id": history_id,
    }
```

- [ ] **Step 2: 运行全部单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/generate_service.py
git commit -m "feat(generate_service): wrap 5 pipeline steps with trace.step()"
```

---

## Task 10: 前端 — api.ts + App.tsx 添加 console.log

**Files:**
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: 修改 `frontend/src/services/api.ts`**

在 `request()` 函数中，`if (!response.ok)` 之前，添加 trace header 提取：

```typescript
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

    // 提取 trace header（在 json() 之前）
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
    // ... 其余不变 ...
```

- [ ] **Step 2: 修改 `frontend/src/App.tsx`**

在 `onCountdownComplete` 的 `setAppState(AppState.ANALYZING)` 前后添加：

```typescript
      // Capture frame
      const base64Photo = captureFrame(video);
      setPhoto(base64Photo);

      // Transition to analyzing
      console.log('[FlowTrace] state:', AppState.ANALYZING, '| action:', 'analyze_start', '| image_size:', base64Photo.length);
      setAppState(AppState.ANALYZING);
```

在 `analyzePhoto` 成功后：

```typescript
      // Analyze photo for style recommendations
      const response = await analyzePhoto(base64Photo);
      setStyleOptions(response.data.options);

      // Transition to style selection
      console.log('[FlowTrace] state:', AppState.STYLE_SELECTION, '| options_count:', response.data.options.length);
      setAppState(AppState.STYLE_SELECTION);
```

在 `handleSelectStyle` 中：

```typescript
      setSelectedOption(style);
      setError(null);
      console.log('[FlowTrace] state:', AppState.GENERATING, '| style:', style.name, '| brief:', style.brief);
      setAppState(AppState.GENERATING);
```

在 generate 成功后：

```typescript
        const response = await generatePoster(photo, style.name, style.brief);
        setPosterUrl(response.data.poster_url);
        console.log('[FlowTrace] state:', AppState.POSTER_READY, '| poster_url:', response.data.poster_url);
        setAppState(AppState.POSTER_READY);
```

- [ ] **Step 3: 运行前端构建确认无 TypeScript 错误**

Run: `cd frontend && npm run build`
Expected: BUILD SUCCESS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/App.tsx
git commit -m "feat(frontend): add FlowTrace console.log at state transitions and API calls"
```

---

## Task 11: 集成测试 — 追加 trace 验证用例

**Files:**
- Modify: `tests/backend/integration/test_real_api.py`

- [ ] **Step 1: 在 test_real_api.py 中添加 verify_trace 辅助函数**

在 `# Helpers` 区域末尾添加：

```python
def verify_trace(flow_type: str, trace_dir: str, trace_id: str | None = None) -> dict:
    """验证 trace 记录。可通过 trace_id 精确匹配，或匹配最新的指定类型 trace。"""
    from app.flow_log.trace_store import TraceStore
    store = TraceStore(trace_dir)
    traces = store.query(limit=50)
    if trace_id:
        matches = [t for t in traces if t.trace_id == trace_id]
        assert len(matches) == 1, f"Expected 1 trace with id={trace_id}, found {len(matches)}"
        trace = matches[0]
    else:
        matches = [t for t in traces if t.flow_type == flow_type]
        assert len(matches) > 0, f"No trace found for {flow_type}"
        trace = matches[0]
    assert trace.flow_type == flow_type
    return trace.model_dump()
```

- [ ] **Step 2: 在现有 T02 测试中追加 trace session 设置和验证**

在 `test_analyze_returns_5_topics` 函数中，`options = asyncio.run(analyze_photo(...))` 之前插入 trace session 设置，在 `print("  [PASS]")` 之前追加验证：

```python
def test_analyze_returns_5_topics():
    """T02: Real LLM returns 5 topic options."""
    print("\n[T02] Analyze — 5 Topics")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    # 手动创建 trace session（集成测试直接调用 service，不走路由层）
    from app.flow_log import FlowSession, set_current_trace
    trace = FlowSession("analyze")
    set_current_trace(trace)

    t0 = time.time()
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    elapsed = time.time() - t0

    assert isinstance(options, list), "Result should be a list"
    assert len(options) == 5, f"Expected 5 options, got {len(options)}"
    print(f"  Options count: {len(options)} (in {elapsed:.1f}s)")

    for i, opt in enumerate(options):
        assert opt.name, f"options[{i}].name is empty"
        assert opt.brief, f"options[{i}].brief is empty"
        assert len(opt.brief) <= 50, f"options[{i}].brief too long ({len(opt.brief)} chars)"
        print(f"  [{i+1}] {opt.name}: {opt.brief}")

    # Verify trace record
    trace.finish("success")
    trace_dir = str(project_root / "data" / "traces")
    from app.flow_log.trace_store import TraceStore
    TraceStore(trace_dir).save(trace.trace)
    trace_data = verify_trace("analyze", trace_dir, trace_id=trace.trace.trace_id)
    assert len(trace_data["steps"]) >= 2, f"Expected >= 2 steps, got {len(trace_data['steps'])}"
    assert trace_data["steps"][0]["name"] == "llm_analyze"
    assert trace_data["steps"][0]["duration_ms"] > 0
    print(f"  Trace: {trace_data['trace_id'][:8]}... ({trace_data['total_duration_ms']:.0f}ms)")
    print("  [PASS]")
    return options
```

- [ ] **Step 3: 在现有 T09 测试中追加 trace session 设置和验证**

在 `test_generate_end_to_end` 函数中，`asyncio.run(generate_artwork(...))` 之前插入 trace session 设置，在 `print("  [PASS]")` 之前追加验证：

```python
    # 在 "Step 3: Generate" 注释之后，asyncio.run(generate_artwork(...)) 之前插入：
    from app.flow_log import FlowSession, set_current_trace
    trace = FlowSession("generate")
    set_current_trace(trace)

    # 在 "Step 5: Validate history" 之后、"print('  [PASS]')" 之前插入：
    trace.finish("success")
    trace_dir = str(project_root / "data" / "traces")
    from app.flow_log.trace_store import TraceStore
    TraceStore(trace_dir).save(trace.trace)
    trace_data = verify_trace("generate", trace_dir, trace_id=trace.trace.trace_id)
    step_names = [s["name"] for s in trace_data["steps"]]
    expected_steps = ["save_photo", "compose_prompt", "image_generate", "save_poster"]
    for expected in expected_steps:
        assert expected in step_names, f"Missing step: {expected} in {step_names}"
    assert trace_data["total_duration_ms"] > 0
    print(f"  Trace: {trace_data['trace_id'][:8]}... ({trace_data['total_duration_ms']:.0f}ms, {len(trace_data['steps'])} steps)")
```

- [ ] **Step 4: 运行集成测试（需真实 API Key）**

Run: `uv run pytest tests/backend/integration/test_real_api.py::test_analyze_returns_5_topics -v -s`
Expected: PASS（含 trace 验证输出）

- [ ] **Step 5: Commit**

```bash
git add tests/backend/integration/test_real_api.py
git commit -m "test(integration): add trace verification to real API tests"
```

---

## Task 12: 最终验证 — 全部测试通过

- [ ] **Step 1: 运行后端全部单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端构建**

Run: `cd frontend && npm run build`
Expected: BUILD SUCCESS

- [ ] **Step 3: 运行前端单元测试**

Run: `cd frontend && npx vitest run`
Expected: 全部 PASS

- [ ] **Step 4: 手动端到端验证**

1. `python start.py` 启动前后端
2. 浏览器 DevTools Console 打开
3. 执行：拍照 → 分析 → 选择主题 → 生成海报
4. Console 中确认每个节点有 `[FlowTrace]` 日志
5. API 响应日志中确认有 `trace_id`
6. 浏览器访问 `http://localhost:8888/api/traces` 确认返回 trace 列表
7. 用返回的 `trace_id` 在 Console 日志和 trace 数据中交叉验证
