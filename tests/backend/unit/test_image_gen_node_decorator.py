"""Tests for @image_gen_node decorator."""

import asyncio
from unittest.mock import MagicMock

import pytest

from app.tracing.context import clear_current_trace, set_current_trace
from app.tracing.decorators import image_gen_node
from app.tracing.models import NodeType
from app.tracing.session import TraceSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(**langsmith_kwargs) -> TraceSession:
    """创建 TraceSession 并设置为当前上下文。"""
    session = TraceSession(flow_type="test", request_id="req-test")
    for attr, val in langsmith_kwargs.items():
        setattr(session, attr, val)
    set_current_trace(session)
    return session


def _cleanup_session() -> None:
    clear_current_trace()


class _FakeRunResult:
    """模拟 LangSmith RunResult。"""

    def __init__(self, run_id: str = "run-img-123", run_url: str = "https://langsmith/run-img-123"):
        self.run_id = run_id
        self.run_url = run_url


def _make_langsmith_mock():
    """创建模拟 LangSmith client。"""
    mock = MagicMock()
    mock.start_run.return_value = _FakeRunResult()
    return mock


# ---------------------------------------------------------------------------
# Test: NoOp (no active session)
# ---------------------------------------------------------------------------


class TestImageGenNodeNoOp:
    """无活跃 session 时，装饰器应完全透传。"""

    def test_function_executes_normally(self):
        """被装饰函数正常执行并返回正确结果。"""

        @image_gen_node(name="noop_img")
        async def my_func(prompt: str) -> str:
            return f"image for {prompt}"

        result = asyncio.get_event_loop().run_until_complete(my_func("a cat"))
        assert result == "image for a cat"

    def test_no_step_created(self):
        """无 session 时不应创建任何步骤。"""

        @image_gen_node(name="noop_img")
        async def my_func() -> str:
            return "ok"

        asyncio.get_event_loop().run_until_complete(my_func())


# ---------------------------------------------------------------------------
# Test: Basic step creation
# ---------------------------------------------------------------------------


class TestImageGenNodeBasic:
    """有活跃 session 时的基本行为。"""

    def test_creates_step_with_node_type_image_gen(self):
        """创建的步骤 node_type 应为 IMAGE_GEN。"""
        session = _make_session()

        @image_gen_node(name="img_step")
        async def my_func() -> str:
            return "short_result"

        asyncio.get_event_loop().run_until_complete(my_func())

        assert len(session.trace.steps) == 1
        step = session.trace.steps[0]
        assert step.name == "img_step"
        assert step.node_type == NodeType.IMAGE_GEN
        assert step.status == "success"

        _cleanup_session()

    def test_duration_ms_is_positive(self):
        """duration_ms 应大于等于 0。"""

        @image_gen_node(name="timed_img")
        async def my_func() -> str:
            await asyncio.sleep(0.01)
            return "done"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.duration_ms > 0

        _cleanup_session()

    def test_captures_input_by_default(self):
        """默认应捕获输入参数。"""

        @image_gen_node(name="input_img")
        async def my_func(prompt: str) -> str:
            return "image"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func(prompt="a cat"))

        step = session.trace.steps[0]
        assert step.input_data is not None
        assert step.input_data.get("prompt") == "a cat"

        _cleanup_session()

    def test_capture_prompt_false(self):
        """capture_prompt=False 时 input_data 应为 None。"""

        @image_gen_node(name="no_prompt_img", capture_prompt=False)
        async def my_func(prompt: str) -> str:
            return "image"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func(prompt="a cat"))

        step = session.trace.steps[0]
        assert step.input_data is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Output handling (no base64 stored)
# ---------------------------------------------------------------------------


class TestImageGenNodeOutput:
    """输出处理 — 不存储完整 base64 数据。"""

    def test_long_string_output_stores_length_not_data(self):
        """长字符串（base64 图片）应只记录长度，不存完整数据。"""
        session = _make_session()

        @image_gen_node(name="b64_img")
        async def my_func() -> str:
            return "x" * 500  # > 200 chars

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.output_data is not None
        assert step.output_data.get("type") == "base64_image"
        assert step.output_data.get("result_length") == 500
        # Should NOT contain the actual data
        assert "result" not in step.output_data or step.output_data.get("type") == "base64_image"

        _cleanup_session()

    def test_short_string_output_uses_normal_serialization(self):
        """短字符串应使用正常的输出序列化。"""
        session = _make_session()

        @image_gen_node(name="short_img")
        async def my_func() -> str:
            return "ok"  # <= 200 chars

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.output_data is not None
        # Short string should go through _serialize_output -> {"result": "ok"}
        assert step.output_data == {"result": "ok"}

        _cleanup_session()

    def test_dict_output_uses_normal_serialization(self):
        """dict 输出应使用正常序列化。"""
        session = _make_session()

        @image_gen_node(name="dict_img")
        async def my_func() -> dict:
            return {"url": "https://example.com/image.png"}

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.output_data == {"url": "https://example.com/image.png"}

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: LangSmith integration
# ---------------------------------------------------------------------------


class TestImageGenNodeLangSmith:
    """LangSmith 上报行为。"""

    def test_langsmith_run_type_is_tool(self):
        """LangSmith run_type 应为 'tool'。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(
            _langsmith=langsmith,
            _langsmith_parent_run_id="parent-run-2",
        )

        @image_gen_node(name="ls_img")
        async def my_func() -> str:
            return "short"

        asyncio.get_event_loop().run_until_complete(my_func())

        langsmith.start_run.assert_called_once_with(
            name="ls_img",
            run_type="tool",
            inputs={"function": "my_func"},
            parent_run_id="parent-run-2",
        )

        _cleanup_session()

    def test_sets_langsmith_run_id(self):
        """有 LangSmith client 时应设置 langsmith_run_id。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(_langsmith=langsmith)

        @image_gen_node(name="ls_id_img")
        async def my_func() -> str:
            return "short"

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.langsmith_run_id is not None
        assert step.langsmith_run_url is not None

        _cleanup_session()

    def test_langsmith_end_run_called_on_success(self):
        """成功时应调用 LangSmith end_run。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(_langsmith=langsmith)

        @image_gen_node(name="ls_end_img")
        async def my_func() -> str:
            return "short"

        asyncio.get_event_loop().run_until_complete(my_func())

        langsmith.end_run.assert_called_once()
        end_call = langsmith.end_run.call_args
        outputs = end_call.kwargs.get("outputs")
        assert outputs == {"status": "success"}

        _cleanup_session()

    def test_no_langsmith_calls_when_no_client(self):
        """无 LangSmith client 时不应报错。"""
        session = _make_session()

        @image_gen_node(name="no_ls_img")
        async def my_func() -> str:
            return "result"

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.langsmith_run_id is None
        assert step.langsmith_run_url is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestImageGenNodeError:
    """异常处理行为。"""

    def test_exception_sets_failed_status_and_reraises(self):
        """函数抛异常时 step.status='failed'，异常 re-raised。"""

        @image_gen_node(name="fail_img")
        async def my_func() -> None:
            raise ValueError("image generation failed")

        session = _make_session()

        with pytest.raises(ValueError, match="image generation failed"):
            asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.status == "failed"
        assert "image generation failed" in step.error

        _cleanup_session()

    def test_error_calls_langsmith_end_run_with_error(self):
        """异常时应调用 LangSmith end_run 并传递 error。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(_langsmith=langsmith)

        @image_gen_node(name="err_ls_img")
        async def my_func() -> None:
            raise ValueError("image error")

        with pytest.raises(ValueError, match="image error"):
            asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.status == "failed"

        langsmith.end_run.assert_called_once()
        end_call = langsmith.end_run.call_args
        assert "image error" in str(end_call)

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: functools.wraps
# ---------------------------------------------------------------------------


class TestImageGenNodeFunctoolsWraps:
    """装饰器应保留被装饰函数的元数据。"""

    def test_preserves_name(self):
        @image_gen_node(name="wrapped")
        async def my_img_func():
            """My image gen function."""
            pass

        assert my_img_func.__name__ == "my_img_func"

    def test_preserves_doc(self):
        @image_gen_node(name="wrapped")
        async def my_img_func():
            """My image gen function."""
            pass

        assert my_img_func.__doc__ == "My image gen function."
