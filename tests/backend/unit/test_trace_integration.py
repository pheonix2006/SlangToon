"""Trace V2 集成测试 — @with_trace + @traceable_node 端到端协作验证。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

from app.schemas.common import ApiResponse, ErrorCode
from app.tracing.context import (
    clear_current_trace,
    get_current_trace,
    reset_current_step_id,
    set_current_step_id,
    set_current_trace,
)
from app.tracing.decorators import traceable_node, with_trace
from app.tracing.models import NodeType
from app.tracing.session import TraceSession


# ── Test 1: Full trace flow ─────────────────────────────────


class TestFullTraceFlow:
    """Route -> Service -> Sub-service: complete DAG trace."""

    @pytest.mark.asyncio
    async def test_full_trace_flow(self):
        """@with_trace 路由 -> @traceable_node 服务 -> @traceable_node 子服务，
        验证完整 DAG 追踪链路。"""
        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "/tmp/test_traces_int"
        settings.trace_retention_days = 7

        @traceable_node("llm_call", node_type=NodeType.LLM)
        async def mock_llm(prompt: str):
            return {"content": "Hello", "tokens": 50}

        @traceable_node("generate_script", node_type=NodeType.CUSTOM)
        async def mock_service(settings=None):
            result = await mock_llm(prompt="test")
            return {"slang": "cool", "result": result}

        @with_trace(
            "script",
            error_map={ValueError: (ErrorCode.SCRIPT_LLM_INVALID, "Bad")},
        )
        async def mock_route(settings=None, response=None):
            data = await mock_service(settings=settings)
            return ApiResponse(data=data)

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            response_mock = MagicMock()
            result = await mock_route(settings=settings, response=response_mock)

        # Verify response
        assert result.code == 0
        assert result.data["slang"] == "cool"

        # Verify trace saved
        mock_store.save.assert_called_once()
        trace = mock_store.save.call_args[0][0]

        # Verify trace structure
        assert trace.flow_type == "script"
        assert trace.status == "success"
        assert len(trace.steps) == 2

        # Verify DAG: service -> llm
        service_step = trace.steps[0]
        llm_step = trace.steps[1]
        assert service_step.name == "generate_script"
        assert llm_step.name == "llm_call"
        assert llm_step.parent_id == service_step.step_id
        assert llm_step.step_id in service_step.children_ids

        # Verify header set
        response_mock.headers.__setitem__.assert_called()


# ── Test 2: Parallel children share same parent ─────────────


class TestParallelChildren:
    """asyncio.gather children all share the same parent step."""

    @pytest.mark.asyncio
    async def test_parallel_children_same_parent(self):
        """asyncio.gather 并行子节点共享同一个 parent step。"""
        session = TraceSession("test", "req-1")
        set_current_trace(session)

        @traceable_node("panel_gen", node_type=NodeType.IMAGE_GEN)
        async def gen_panel(idx: int):
            return f"panel_{idx}"

        parent = session.create_step("comic_gen", NodeType.CUSTOM)
        token = set_current_step_id(parent.step_id)

        results = await asyncio.gather(
            gen_panel(idx=1),
            gen_panel(idx=2),
            gen_panel(idx=3),
        )

        reset_current_step_id(token)
        clear_current_trace()

        assert results == ["panel_1", "panel_2", "panel_3"]
        children = [s for s in session.trace.steps if s.parent_id == parent.step_id]
        assert len(children) == 3
        assert len(parent.children_ids) == 3


# ── Test 3: Error handling in trace flow ─────────────────────


class TestTraceFlowErrors:
    """Error propagation through trace decorators."""

    @pytest.mark.asyncio
    async def test_trace_flow_catches_mapped_error(self):
        """@with_trace 捕获 error_map 中映射的异常并返回 ApiResponse。"""
        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "/tmp/test_traces_int"
        settings.trace_retention_days = 7

        @traceable_node("failing_node", node_type=NodeType.CUSTOM)
        async def failing_service():
            raise ValueError("bad input")

        @with_trace(
            "script",
            error_map={ValueError: (ErrorCode.SCRIPT_LLM_INVALID, "Bad")},
        )
        async def mock_route(settings=None, response=None):
            await failing_service()
            return ApiResponse(data={})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            response_mock = MagicMock()
            result = await mock_route(settings=settings, response=response_mock)

        # Verify error response
        assert result.code == ErrorCode.SCRIPT_LLM_INVALID
        assert result.message == "Bad"
        assert result.data is None

        # Verify trace recorded as failed
        mock_store.save.assert_called_once()
        trace = mock_store.save.call_args[0][0]
        assert trace.status == "failed"
        assert trace.error is not None
        assert "bad input" in trace.error

        # The failing node step should have status "failed"
        failed_step = next(
            (s for s in trace.steps if s.name == "failing_node"), None
        )
        assert failed_step is not None
        assert failed_step.status == "failed"
        assert "bad input" in (failed_step.error or "")

    @pytest.mark.asyncio
    async def test_trace_flow_catches_unmapped_error(self):
        """@with_trace 捕获未映射的异常并返回 INTERNAL_ERROR。"""
        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "/tmp/test_traces_int"
        settings.trace_retention_days = 7

        @traceable_node("boom", node_type=NodeType.CUSTOM)
        async def boom_service():
            raise RuntimeError("unexpected")

        @with_trace("comic", error_map={})
        async def mock_route(settings=None, response=None):
            await boom_service()
            return ApiResponse(data={})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            response_mock = MagicMock()
            result = await mock_route(settings=settings, response=response_mock)

        assert result.code == ErrorCode.INTERNAL_ERROR
        assert "unexpected" in result.message

        trace = mock_store.save.call_args[0][0]
        assert trace.status == "failed"

    @pytest.mark.asyncio
    async def test_noop_when_trace_disabled(self):
        """trace_enabled=False 时不创建 trace，直接透传。"""
        settings = MagicMock()
        settings.trace_enabled = False

        @traceable_node("node", node_type=NodeType.CUSTOM)
        async def simple_node():
            return "ok"

        @with_trace("script")
        async def mock_route(settings=None, response=None):
            result = await simple_node()
            return ApiResponse(data={"result": result})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            result = await mock_route(settings=settings, response=MagicMock())

        assert result.code == 0
        assert result.data["result"] == "ok"
        mock_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_without_settings(self):
        """settings=None 时不创建 trace，直接透传。"""
        @traceable_node("node", node_type=NodeType.CUSTOM)
        async def simple_node():
            return "ok"

        @with_trace("script")
        async def mock_route(settings=None, response=None):
            result = await simple_node()
            return ApiResponse(data={"result": result})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            result = await mock_route(response=MagicMock())

        assert result.code == 0
        mock_store.save.assert_not_called()


# ── Test 4: Nested DAG structure ─────────────────────────────


class TestNestedDAG:
    """Deep nesting: route -> service -> sub-service -> leaf."""

    @pytest.mark.asyncio
    async def test_three_level_nesting(self):
        """三层嵌套：route -> service -> sub_service -> leaf，验证完整 DAG。"""
        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "/tmp/test_traces_int"
        settings.trace_retention_days = 7

        @traceable_node("leaf", node_type=NodeType.LLM)
        async def leaf_node(text: str):
            return f"processed_{text}"

        @traceable_node("sub_service", node_type=NodeType.PROMPT)
        async def sub_service(input_text: str):
            return await leaf_node(text=input_text)

        @traceable_node("main_service", node_type=NodeType.CUSTOM)
        async def main_service():
            return await sub_service(input_text="hello")

        @with_trace("comic")
        async def mock_route(settings=None, response=None):
            data = await main_service()
            return ApiResponse(data={"output": data})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            result = await mock_route(settings=settings, response=MagicMock())

        assert result.code == 0
        mock_store.save.assert_called_once()
        trace = mock_store.save.call_args[0][0]

        assert trace.status == "success"
        assert len(trace.steps) == 3

        # Steps in order: main_service, sub_service, leaf
        main_step = trace.steps[0]
        sub_step = trace.steps[1]
        leaf_step = trace.steps[2]

        assert main_step.name == "main_service"
        assert sub_step.name == "sub_service"
        assert leaf_step.name == "leaf"

        # Verify parent-child: main -> sub -> leaf
        assert sub_step.parent_id == main_step.step_id
        assert sub_step.step_id in main_step.children_ids
        assert leaf_step.parent_id == sub_step.step_id
        assert leaf_step.step_id in sub_step.children_ids

        # Leaf has no children
        assert len(leaf_step.children_ids) == 0

        # Root step is main_service
        assert trace.root_step_id == main_step.step_id


# ── Test 5: Step status and timing ──────────────────────────


class TestStepStatusAndTiming:
    """Verify step status, timing, and input/output capture."""

    @pytest.mark.asyncio
    async def test_step_captures_input_and_output(self):
        """@traceable_node 捕获输入和输出数据。"""
        session = TraceSession("test", "req-2")
        set_current_trace(session)

        @traceable_node(
            "with_io",
            node_type=NodeType.CUSTOM,
            capture_input=True,
            capture_output=True,
        )
        async def node_with_io(name: str, count: int):
            return {"result": f"{name}_{count}"}

        result = await node_with_io(name="test", count=42)
        clear_current_trace()

        assert result == {"result": "test_42"}

        step = session.trace.steps[0]
        assert step.input_data is not None
        assert step.input_data.get("name") == "test"
        assert step.input_data.get("count") == 42
        assert step.output_data is not None
        assert step.output_data.get("result") == "test_42"

    @pytest.mark.asyncio
    async def test_step_records_duration(self):
        """每个步骤记录了 duration_ms > 0。"""
        session = TraceSession("test", "req-3")
        set_current_trace(session)

        @traceable_node("timed", node_type=NodeType.CUSTOM)
        async def timed_node():
            await asyncio.sleep(0.01)
            return "done"

        await timed_node()
        clear_current_trace()

        step = session.trace.steps[0]
        assert step.status == "success"
        assert step.duration_ms > 0

    @pytest.mark.asyncio
    async def test_trace_records_total_duration(self):
        """@with_trace 记录总耗时。"""
        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "/tmp/test_traces_int"
        settings.trace_retention_days = 7

        @traceable_node("slow", node_type=NodeType.CUSTOM)
        async def slow_node():
            await asyncio.sleep(0.02)
            return "ok"

        @with_trace("script")
        async def mock_route(settings=None, response=None):
            await slow_node()
            return ApiResponse(data={})

        mock_store = MagicMock()
        with patch(
            "app.tracing.decorators.get_trace_v2_store", return_value=mock_store
        ):
            await mock_route(settings=settings, response=MagicMock())

        trace = mock_store.save.call_args[0][0]
        assert trace.total_duration_ms > 0
