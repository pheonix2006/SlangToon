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
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


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
