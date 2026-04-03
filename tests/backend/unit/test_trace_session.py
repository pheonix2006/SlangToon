"""TraceSession 单元测试 — 覆盖 FlowTrace 生命周期管理和 DAG 步骤创建。"""

import asyncio
import time

import pytest

from app.tracing.models import FlowStep, FlowTrace, NodeType
from app.tracing.session import TraceSession


# ── 创建与初始化 ──────────────────────────────────────────


class TestSessionCreation:
    """Session 创建时 FlowTrace 初始化字段验证。"""

    def test_creates_trace_with_correct_fields(self):
        session = TraceSession(flow_type="script", request_id="req-001")

        trace = session.trace
        assert isinstance(trace, FlowTrace)
        assert trace.trace_id.startswith("t-")
        assert len(trace.trace_id) == 14  # "t-" + 12 hex chars
        assert trace.request_id == "req-001"
        assert trace.flow_type == "script"
        assert trace.steps == []
        assert trace.root_step_id is None
        assert trace.status == "running"
        assert trace.error is None

    def test_trace_id_uniqueness(self):
        """两次创建 session 应产生不同的 trace_id。"""
        s1 = TraceSession(flow_type="a", request_id="r1")
        s2 = TraceSession(flow_type="a", request_id="r2")
        assert s1.trace.trace_id != s2.trace.trace_id

    def test_created_at_is_iso_format(self):
        session = TraceSession(flow_type="comic", request_id="req-002")
        # 验证 created_at 非空且包含 T（ISO 格式基本特征）
        assert "T" in session.trace.created_at


# ── create_step / DAG 构建 ────────────────────────────────


class TestCreateStep:
    """步骤创建与 DAG 父子关系。"""

    def test_first_step_with_no_parent_becomes_root(self):
        session = TraceSession(flow_type="script", request_id="r1")
        step = session.create_step("root", NodeType.LLM)

        assert isinstance(step, FlowStep)
        assert step.step_id.startswith("s-")
        assert step.name == "root"
        assert step.node_type == NodeType.LLM
        assert step.parent_id is None
        assert step in session.trace.steps
        assert session.trace.root_step_id == step.step_id

    def test_child_step_gets_correct_parent_and_updates_children_ids(self):
        session = TraceSession(flow_type="script", request_id="r1")
        parent = session.create_step("parent", NodeType.LLM)
        child = session.create_step("child", NodeType.PROMPT, parent_id=parent.step_id)

        assert child.parent_id == parent.step_id
        assert child.step_id in parent.children_ids
        assert child in session.trace.steps
        # root 不变
        assert session.trace.root_step_id == parent.step_id

    def test_multiple_children_share_same_parent(self):
        session = TraceSession(flow_type="script", request_id="r1")
        parent = session.create_step("root", NodeType.LLM)
        c1 = session.create_step("child1", NodeType.PROMPT, parent_id=parent.step_id)
        c2 = session.create_step("child2", NodeType.IO, parent_id=parent.step_id)
        c3 = session.create_step("child3", NodeType.CUSTOM, parent_id=parent.step_id)

        assert len(parent.children_ids) == 3
        assert c1.step_id in parent.children_ids
        assert c2.step_id in parent.children_ids
        assert c3.step_id in parent.children_ids

    def test_deep_nesting_s1_s2_s3(self):
        """三层嵌套：s1 → s2 → s3，每层链接正确。"""
        session = TraceSession(flow_type="comic", request_id="r1")

        s1 = session.create_step("level1", NodeType.LLM)
        s2 = session.create_step("level2", NodeType.PROMPT, parent_id=s1.step_id)
        s3 = session.create_step("level3", NodeType.IMAGE_GEN, parent_id=s2.step_id)

        # s1 是根
        assert session.trace.root_step_id == s1.step_id
        # s1 的 child 是 s2
        assert s2.step_id in s1.children_ids
        # s2 的 child 是 s3
        assert s3.step_id in s2.children_ids
        # s3 没有 child
        assert s3.children_ids == []
        # s3 的 parent 是 s2
        assert s3.parent_id == s2.step_id

    def test_step_id_uniqueness(self):
        session = TraceSession(flow_type="x", request_id="r1")
        s1 = session.create_step("a", NodeType.LLM)
        s2 = session.create_step("b", NodeType.LLM)
        assert s1.step_id != s2.step_id

    def test_started_at_is_set(self):
        session = TraceSession(flow_type="x", request_id="r1")
        step = session.create_step("step", NodeType.IO)
        assert "T" in step.started_at  # ISO 格式基本特征


# ── _find_step ────────────────────────────────────────────


class TestFindStep:
    """_find_step 内部方法。"""

    def test_find_existing_step(self):
        session = TraceSession(flow_type="x", request_id="r1")
        step = session.create_step("target", NodeType.LLM)

        found = session._find_step(step.step_id)
        assert found is step

    def test_find_missing_returns_none(self):
        session = TraceSession(flow_type="x", request_id="r1")
        session.create_step("other", NodeType.LLM)

        found = session._find_step("s-nonexistent")
        assert found is None


# ── finish ────────────────────────────────────────────────


class TestFinish:
    """finish 方法设置状态和计算耗时。"""

    def test_finish_success_sets_status(self):
        session = TraceSession(flow_type="x", request_id="r1")
        session.finish("success")

        assert session.trace.status == "success"
        assert session.trace.total_duration_ms >= 0
        assert session.trace.error is None

    def test_finish_failed_sets_error(self):
        session = TraceSession(flow_type="x", request_id="r1")
        session.finish("failed", error="timeout")

        assert session.trace.status == "failed"
        assert session.trace.error == "timeout"

    def test_finish_calculates_real_duration(self):
        """休眠后验证 duration >= 10ms。"""
        session = TraceSession(flow_type="x", request_id="r1")
        time.sleep(0.02)  # 20ms
        session.finish("success")

        assert session.trace.total_duration_ms >= 10

    @pytest.mark.asyncio
    async def test_finish_duration_with_async_sleep(self):
        session = TraceSession(flow_type="x", request_id="r1")
        await asyncio.sleep(0.02)
        session.finish("success")

        assert session.trace.total_duration_ms >= 10
