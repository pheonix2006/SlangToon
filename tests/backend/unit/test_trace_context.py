"""测试 Trace V2 ContextVars 管理 — trace session 和 step_id 的传播与隔离。"""

import asyncio

import pytest

from app.tracing.context import (
    clear_current_trace,
    get_current_step_id,
    get_current_trace,
    reset_current_step_id,
    set_current_step_id,
    set_current_trace,
)


@pytest.fixture(autouse=True)
def _clean_context():
    """每个测试前后清理 ContextVar 状态，防止测试间泄漏。"""
    clear_current_trace()
    token = set_current_step_id(None)
    yield
    reset_current_step_id(token)
    clear_current_trace()


# ── 辅助：轻量 mock 对象，替代真实 TraceSession ──


class _FakeSession:
    """用于测试的最小 TraceSession 替身。"""

    def __init__(self, trace_id: str = "t-001"):
        self.trace_id = trace_id


# ═══════════════════════════════════════════
# 1. 默认值测试
# ═══════════════════════════════════════════


class TestDefaults:
    """未设置时，get 应返回 None。"""

    def test_trace_default_is_none(self):
        assert get_current_trace() is None

    def test_step_id_default_is_none(self):
        assert get_current_step_id() is None


# ═══════════════════════════════════════════
# 2. Trace session set / get 往返测试
# ═══════════════════════════════════════════


class TestTraceRoundtrip:
    """set 后 get 应返回同一对象。"""

    def test_set_and_get_trace(self):
        session = _FakeSession("t-100")
        set_current_trace(session)
        assert get_current_trace() is session

    def test_set_different_sessions(self):
        s1 = _FakeSession("t-001")
        s2 = _FakeSession("t-002")
        set_current_trace(s1)
        assert get_current_trace() is s1
        set_current_trace(s2)
        assert get_current_trace() is s2


# ═══════════════════════════════════════════
# 3. clear_current_trace
# ═══════════════════════════════════════════


class TestClearTrace:
    """clear 应将 trace 重置为 None。"""

    def test_clear_resets_to_none(self):
        set_current_trace(_FakeSession("t-999"))
        assert get_current_trace() is not None
        clear_current_trace()
        assert get_current_trace() is None


# ═══════════════════════════════════════════
# 4. step_id Token 机制
# ═══════════════════════════════════════════


class TestStepIdToken:
    """set_current_step_id 返回 Token，reset 恢复前值。"""

    def test_set_returns_token_type(self):
        token = set_current_step_id("s-1")
        # Token 是 contextvars.Token 实例
        from contextvars import Token

        assert isinstance(token, Token)

    def test_reset_restores_previous_value(self):
        assert get_current_step_id() is None
        token = set_current_step_id("s-1")
        assert get_current_step_id() == "s-1"
        reset_current_step_id(token)
        assert get_current_step_id() is None


# ═══════════════════════════════════════════
# 5. 嵌套 set / reset 模式
# ═══════════════════════════════════════════


class TestNestedSetReset:
    """多层嵌套 set/reset 应正确恢复每一层。"""

    def test_nested_two_levels(self):
        assert get_current_step_id() is None

        token1 = set_current_step_id("s-1")
        assert get_current_step_id() == "s-1"

        token2 = set_current_step_id("s-2")
        assert get_current_step_id() == "s-2"

        # 回退到 s-1
        reset_current_step_id(token2)
        assert get_current_step_id() == "s-1"

        # 回退到 None
        reset_current_step_id(token1)
        assert get_current_step_id() is None

    def test_nested_three_levels(self):
        assert get_current_step_id() is None

        t1 = set_current_step_id("level-1")
        t2 = set_current_step_id("level-2")
        t3 = set_current_step_id("level-3")

        assert get_current_step_id() == "level-3"

        reset_current_step_id(t3)
        assert get_current_step_id() == "level-2"

        reset_current_step_id(t2)
        assert get_current_step_id() == "level-1"

        reset_current_step_id(t1)
        assert get_current_step_id() is None


# ═══════════════════════════════════════════
# 6. asyncio.gather 并行隔离
# ═══════════════════════════════════════════


class TestAsyncIsolation:
    """contextvars 自动按 asyncio task 复制，并行协程互不干扰。"""

    @pytest.mark.asyncio
    async def test_parallel_step_id_isolation(self):
        """每个并行协程应看到自己设置的 step_id，不受其他协程影响。"""

        # 先在父上下文中设置一个 step_id
        parent_token = set_current_step_id("parent-step")

        async def worker(step_id: str) -> str:
            token = set_current_step_id(step_id)
            await asyncio.sleep(0.01)  # 让出控制权，增加交错概率
            value = get_current_step_id()
            reset_current_step_id(token)
            return value

        results = await asyncio.gather(
            worker("worker-A"),
            worker("worker-B"),
            worker("worker-C"),
        )

        assert results == ["worker-A", "worker-B", "worker-C"]

        # 父上下文应保持不变
        assert get_current_step_id() == "parent-step"
        reset_current_step_id(parent_token)
        assert get_current_step_id() is None

    @pytest.mark.asyncio
    async def test_parallel_trace_session_isolation(self):
        """并行协程各自设置 trace session 不互相干扰。"""

        async def worker(trace_id: str) -> str | None:
            session = _FakeSession(trace_id)
            set_current_trace(session)
            await asyncio.sleep(0.01)
            current = get_current_trace()
            return current.trace_id if current else None

        results = await asyncio.gather(
            worker("trace-X"),
            worker("trace-Y"),
            worker("trace-Z"),
        )

        assert results == ["trace-X", "trace-Y", "trace-Z"]
