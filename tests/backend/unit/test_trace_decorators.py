"""Tests for @traceable_node and @with_trace decorators."""

import asyncio

import pytest
from unittest.mock import MagicMock, patch

from app.tracing.context import (
    clear_current_trace,
    get_current_step_id,
    get_current_trace,
    set_current_step_id,
    set_current_trace,
)
from app.tracing.decorators import traceable_node, with_trace
from app.tracing.models import NodeType
from app.tracing.session import TraceSession
from app.schemas.common import ApiResponse, ErrorCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session() -> TraceSession:
    """创建一个 TraceSession 并设置为当前上下文。"""
    session = TraceSession(flow_type="test", request_id="req-test")
    set_current_trace(session)
    return session


def _cleanup_session() -> None:
    """清除当前上下文的 trace session。"""
    clear_current_trace()


# ---------------------------------------------------------------------------
# Test: NoOp (no active session)
# ---------------------------------------------------------------------------

class TestTraceableNodeNoOp:
    """无活跃 session 时，装饰器应完全透传。"""

    def test_function_executes_normally_returns_correct_result(self):
        """被装饰函数正常执行并返回正确结果。"""

        @traceable_node(name="noop_func")
        async def my_func(x: int, y: int) -> int:
            return x + y

        result = asyncio.run(my_func(3, 4))
        assert result == 7

    def test_no_step_created(self):
        """无 session 时不应创建任何步骤。"""
        assert get_current_trace() is None

        @traceable_node(name="noop_func")
        async def my_func() -> str:
            return "ok"

        asyncio.run(my_func())
        # 无 session，trace 仍为 None
        assert get_current_trace() is None


# ---------------------------------------------------------------------------
# Test: Basic (with session)
# ---------------------------------------------------------------------------

class TestTraceableNodeBasic:
    """有活跃 session 时的基本行为。"""

    def test_creates_step_with_correct_properties(self):
        """创建的步骤具有正确的 name、node_type 和 status。"""
        session = _make_session()

        @traceable_node(name="my_step", node_type=NodeType.LLM)
        async def my_func() -> str:
            return "done"

        asyncio.run(my_func())

        assert len(session.trace.steps) == 1
        step = session.trace.steps[0]
        assert step.name == "my_step"
        assert step.node_type == NodeType.LLM
        assert step.status == "success"
        assert step.error is None

        _cleanup_session()

    def test_duration_ms_is_positive(self):
        """duration_ms 应大于 0。"""

        @traceable_node(name="timed_step")
        async def slow_func() -> str:
            await asyncio.sleep(0.01)
            return "slow"

        session = _make_session()
        asyncio.run(slow_func())

        step = session.trace.steps[0]
        assert step.duration_ms > 0

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Input Capture
# ---------------------------------------------------------------------------

class TestTraceableNodeInputCapture:
    """输入参数捕获行为。"""

    def test_captures_kwargs(self):
        """捕获 kwargs 参数。"""

        @traceable_node(name="input_func")
        async def my_func(name: str, value: int) -> str:
            return f"{name}={value}"

        session = _make_session()
        asyncio.run(
            my_func(name="test", value=42)
        )

        step = session.trace.steps[0]
        assert step.input_data is not None
        assert step.input_data["name"] == "test"
        assert step.input_data["value"] == 42

        _cleanup_session()

    def test_excludes_sensitive_params(self):
        """排除敏感参数（settings、api_key 等）。"""

        @traceable_node(name="sensitive_func")
        async def my_func(settings: str, api_key: str, data: str) -> str:
            return "ok"

        session = _make_session()
        asyncio.run(
            my_func(settings="s", api_key="secret", data="visible")
        )

        step = session.trace.steps[0]
        assert step.input_data is not None
        assert "settings" not in step.input_data
        assert "api_key" not in step.input_data
        assert step.input_data["data"] == "visible"

        _cleanup_session()

    def test_truncates_long_strings(self):
        """超过 2000 字符的字符串应被截断。"""
        long_str = "x" * 3000

        @traceable_node(name="truncate_func")
        async def my_func(text: str) -> str:
            return "ok"

        session = _make_session()
        asyncio.run(my_func(text=long_str))

        step = session.trace.steps[0]
        assert step.input_data is not None
        truncated = step.input_data["text"]
        assert truncated.endswith("[TRUNCATED]")
        assert len(truncated) == 2000 + len("[TRUNCATED]")

        _cleanup_session()

    def test_capture_input_false(self):
        """capture_input=False 时 input_data 应为 None。"""

        @traceable_node(name="no_input", capture_input=False)
        async def my_func(val: str) -> str:
            return val

        session = _make_session()
        asyncio.run(my_func(val="x"))

        step = session.trace.steps[0]
        assert step.input_data is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Output Capture
# ---------------------------------------------------------------------------

class TestTraceableNodeOutputCapture:
    """输出捕获行为。"""

    def test_dict_output(self):
        """dict 输出应直接存储。"""

        @traceable_node(name="dict_out")
        async def my_func() -> dict:
            return {"key": "value"}

        session = _make_session()
        asyncio.run(my_func())

        step = session.trace.steps[0]
        assert step.output_data == {"key": "value"}

        _cleanup_session()

    def test_string_output(self):
        """非 dict 输出应包装为 {"result": ...}。"""

        @traceable_node(name="str_out")
        async def my_func() -> str:
            return "hello"

        session = _make_session()
        asyncio.run(my_func())

        step = session.trace.steps[0]
        assert step.output_data == {"result": "hello"}

        _cleanup_session()

    def test_capture_output_false(self):
        """capture_output=False 时 output_data 应为 None。"""

        @traceable_node(name="no_output", capture_output=False)
        async def my_func() -> str:
            return "secret"

        session = _make_session()
        asyncio.run(my_func())

        step = session.trace.steps[0]
        assert step.output_data is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Nesting
# ---------------------------------------------------------------------------

class TestTraceableNodeNesting:
    """嵌套装饰器应正确设置 parent_id。"""

    def test_inner_parent_id_equals_outer_step_id(self):
        """内层步骤的 parent_id 应等于外层步骤的 step_id。"""

        @traceable_node(name="outer")
        async def outer_func() -> str:
            return await inner_func()

        @traceable_node(name="inner")
        async def inner_func() -> str:
            return "nested"

        session = _make_session()
        asyncio.run(outer_func())

        assert len(session.trace.steps) == 2
        outer_step = session.trace.steps[0]
        inner_step = session.trace.steps[1]

        assert outer_step.name == "outer"
        assert inner_step.name == "inner"
        assert inner_step.parent_id == outer_step.step_id
        assert inner_step.step_id in outer_step.children_ids

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Error Handling
# ---------------------------------------------------------------------------

class TestTraceableNodeError:
    """异常处理行为。"""

    def test_exception_sets_failed_status_and_reraises(self):
        """函数抛异常时 step.status='failed'，step.error 有信息，异常 re-raised。"""

        @traceable_node(name="fail_func")
        async def my_func() -> None:
            raise ValueError("something went wrong")

        session = _make_session()

        with pytest.raises(ValueError, match="something went wrong"):
            asyncio.run(my_func())

        step = session.trace.steps[0]
        assert step.status == "failed"
        assert "something went wrong" in step.error
        assert step.duration_ms >= 0

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Custom Serializers
# ---------------------------------------------------------------------------

class TestTraceableNodeCustomSerializer:
    """自定义序列化器。"""

    def test_input_serializer(self):
        """input_serializer 自定义输入序列化。"""

        def my_input_serializer(args, kwargs):
            return {"prompt": kwargs.get("text", "")[:10]}

        @traceable_node(
            name="custom_in",
            input_serializer=my_input_serializer,
        )
        async def my_func(text: str) -> str:
            return text

        session = _make_session()
        asyncio.run(
            my_func(text="Hello World 12345")
        )

        step = session.trace.steps[0]
        assert step.input_data == {"prompt": "Hello Worl"}

        _cleanup_session()

    def test_output_serializer(self):
        """output_serializer 自定义输出序列化。"""

        def my_output_serializer(result):
            return {"length": len(result)}

        @traceable_node(
            name="custom_out",
            output_serializer=my_output_serializer,
        )
        async def my_func() -> str:
            return "abcdefghij"

        session = _make_session()
        asyncio.run(my_func())

        step = session.trace.steps[0]
        assert step.output_data == {"length": 10}

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: @with_trace basic
# ---------------------------------------------------------------------------

class TestWithTraceBasic:
    """@with_trace 路由级装饰器基本行为。"""

    def test_creates_session_when_trace_enabled(self):
        """trace_enabled=True 时应创建 session 并设置为当前上下文。"""

        captured_session = None

        @with_trace("test_flow")
        async def my_func(**kwargs):
            nonlocal captured_session
            captured_session = get_current_trace()
            return ApiResponse(data={"ok": True})

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_store:
            mock_store.return_value = MagicMock()
            result = asyncio.run(
                my_func(settings=settings)
            )

        assert result.code == 0
        assert captured_session is not None
        assert captured_session.trace.flow_type == "test_flow"
        assert captured_session.trace.status == "success"

    def test_noop_when_trace_enabled_false(self):
        """trace_enabled=False 时应完全跳过追踪。"""

        inner_called = False

        @with_trace("test_flow")
        async def my_func(**kwargs):
            nonlocal inner_called
            inner_called = True
            return ApiResponse(data={"ok": True})

        settings = MagicMock()
        settings.trace_enabled = False

        result = asyncio.run(
            my_func(settings=settings)
        )

        assert inner_called is True
        assert result.code == 0

    def test_noop_when_no_settings_kwarg(self):
        """无 settings 参数时应完全跳过追踪。"""

        @with_trace("test_flow")
        async def my_func(**kwargs):
            return ApiResponse(data={"ok": True})

        result = asyncio.run(my_func())

        assert result.code == 0

    def test_sets_trace_id_header_in_response(self):
        """应在 response 对象上设置 x-trace-id header。"""

        @with_trace("test_flow")
        async def my_func(**kwargs):
            return ApiResponse(data={"ok": True})

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7
        response = MagicMock()
        response.headers = {}

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_store:
            mock_store.return_value = MagicMock()
            asyncio.run(
                my_func(settings=settings, response=response)
            )

        assert "x-trace-id" in response.headers
        assert response.headers["x-trace-id"].startswith("t-")


# ---------------------------------------------------------------------------
# Test: @with_trace error mapping
# ---------------------------------------------------------------------------

class TestWithTraceErrorMapping:
    """@with_trace 异常映射行为。"""

    def test_maps_known_exception(self):
        """已知异常应映射为自定义错误码。"""

        @with_trace(
            "test_flow",
            error_map={ValueError: (40001, "Custom error")},
        )
        async def my_func(**kwargs):
            raise ValueError("bad input")

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_store:
            mock_store.return_value = MagicMock()
            result = asyncio.run(
                my_func(settings=settings)
            )

        assert result.code == 40001
        assert result.message == "Custom error"
        assert result.data is None

    def test_unmapped_exception_returns_internal_error(self):
        """未映射的异常应返回 INTERNAL_ERROR。"""

        @with_trace("test_flow")
        async def my_func(**kwargs):
            raise RuntimeError("unexpected")

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_store:
            mock_store.return_value = MagicMock()
            result = asyncio.run(
                my_func(settings=settings)
            )

        assert result.code == ErrorCode.INTERNAL_ERROR
        assert "unexpected" in result.message

    def test_saves_trace_on_error(self):
        """出错时也应保存 trace，且 trace.status 为 'failed'。"""

        saved_trace = None

        @with_trace("test_flow")
        async def my_func(**kwargs):
            raise ValueError("boom")

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7

        mock_store_instance = MagicMock()

        def capture_save(trace):
            nonlocal saved_trace
            saved_trace = trace

        mock_store_instance.save.side_effect = capture_save

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_get_store:
            mock_get_store.return_value = mock_store_instance
            asyncio.run(
                my_func(settings=settings)
            )

        mock_store_instance.save.assert_called_once()
        assert saved_trace is not None
        assert saved_trace.status == "failed"

    def test_clears_context_in_finally(self):
        """finally 块应清除当前 trace 上下文。"""

        @with_trace("test_flow")
        async def my_func(**kwargs):
            return ApiResponse(data={"ok": True})

        settings = MagicMock()
        settings.trace_enabled = True
        settings.trace_dir = "data/traces"
        settings.trace_retention_days = 7

        with patch("app.tracing.decorators.get_trace_v2_store") as mock_store:
            mock_store.return_value = MagicMock()
            asyncio.run(
                my_func(settings=settings)
            )

        assert get_current_trace() is None


# ---------------------------------------------------------------------------
# Test: @with_trace functools.wraps
# ---------------------------------------------------------------------------

class TestWithTraceFunctoolsWraps:
    """@with_trace 应保留被装饰函数的元数据。"""

    def test_preserves_name(self):
        @with_trace("test_flow")
        async def my_special_func(**kwargs):
            """This is my special function."""
            pass

        assert my_special_func.__name__ == "my_special_func"

    def test_preserves_doc(self):
        @with_trace("test_flow")
        async def my_special_func(**kwargs):
            """This is my special function."""
            pass

        assert my_special_func.__doc__ == "This is my special function."
