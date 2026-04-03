"""Tests for @llm_node decorator."""

import asyncio
from unittest.mock import MagicMock

import pytest

from app.tracing.context import clear_current_trace, set_current_trace
from app.tracing.decorators import llm_node
from app.tracing.models import LLMMeta, NodeType
from app.tracing.session import TraceSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(**langsmith_kwargs) -> TraceSession:
    """创建 TraceSession 并设置为当前上下文。

    可选通过 langsmith_kwargs 设置 _langsmith 和 _langsmith_parent_run_id。
    """
    session = TraceSession(flow_type="test", request_id="req-test")
    for attr, val in langsmith_kwargs.items():
        setattr(session, attr, val)
    set_current_trace(session)
    return session


def _cleanup_session() -> None:
    clear_current_trace()


class _FakeLLMResult:
    """模拟 LLM 返回结果，携带 model / token 用量属性。"""

    def __init__(
        self,
        content: str = "hello",
        model: str = "glm-4.6v",
        prompt_tokens: int = 10,
        completion_tokens: int = 20,
        total_tokens: int = 30,
        finish_reason: str = "stop",
    ):
        self.content = content
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.finish_reason = finish_reason
        self.usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }


class _FakeRunResult:
    """模拟 LangSmith RunResult。"""

    def __init__(self, run_id: str = "run-123", run_url: str = "https://langsmith/run-123"):
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


class TestLLMNodeNoOp:
    """无活跃 session 时，装饰器应完全透传。"""

    def test_function_executes_normally(self):
        """被装饰函数正常执行并返回正确结果。"""

        @llm_node(name="noop_llm")
        async def my_func(x: int) -> int:
            return x * 2

        result = asyncio.get_event_loop().run_until_complete(my_func(5))
        assert result == 10

    def test_no_step_created(self):
        """无 session 时不应创建任何步骤。"""

        @llm_node(name="noop_llm")
        async def my_func() -> str:
            return "ok"

        asyncio.get_event_loop().run_until_complete(my_func())
        # session 仍为 None，无异常


# ---------------------------------------------------------------------------
# Test: Basic step creation
# ---------------------------------------------------------------------------


class TestLLMNodeBasic:
    """有活跃 session 时的基本行为。"""

    def test_creates_step_with_node_type_llm(self):
        """创建的步骤 node_type 应为 LLM。"""
        session = _make_session()

        @llm_node(name="llm_step")
        async def my_func() -> str:
            return "result"

        asyncio.get_event_loop().run_until_complete(my_func())

        assert len(session.trace.steps) == 1
        step = session.trace.steps[0]
        assert step.name == "llm_step"
        assert step.node_type == NodeType.LLM
        assert step.status == "success"

        _cleanup_session()

    def test_duration_ms_is_positive(self):
        """duration_ms 应大于等于 0。"""

        @llm_node(name="timed_llm")
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

        @llm_node(name="input_llm")
        async def my_func(prompt: str) -> str:
            return "response"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func(prompt="hello"))

        step = session.trace.steps[0]
        assert step.input_data is not None
        assert step.input_data.get("prompt") == "hello"

        _cleanup_session()

    def test_captures_output_by_default(self):
        """默认应捕获输出。"""

        @llm_node(name="output_llm")
        async def my_func() -> dict:
            return {"text": "response"}

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.output_data is not None
        assert step.output_data.get("text") == "response"

        _cleanup_session()

    def test_capture_prompt_false(self):
        """capture_prompt=False 时 input_data 应为 None。"""

        @llm_node(name="no_prompt", capture_prompt=False)
        async def my_func(prompt: str) -> str:
            return "response"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func(prompt="hello"))

        step = session.trace.steps[0]
        assert step.input_data is None

        _cleanup_session()

    def test_capture_response_false(self):
        """capture_response=False 时 output_data 应为 None。"""

        @llm_node(name="no_response", capture_response=False)
        async def my_func() -> str:
            return "response"

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.output_data is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: LLMMeta extraction
# ---------------------------------------------------------------------------


class TestLLMNodeMetaExtraction:
    """LLMMeta 从返回结果中提取。"""

    def test_extracts_llm_meta_from_result(self):
        """从结果对象中提取 LLMMeta。"""

        @llm_node(name="meta_llm")
        async def my_func() -> _FakeLLMResult:
            return _FakeLLMResult(
                content="hello world",
                model="glm-4.6v",
                prompt_tokens=15,
                completion_tokens=25,
                total_tokens=40,
                finish_reason="stop",
            )

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.llm_meta is not None
        assert step.llm_meta.model == "glm-4.6v"
        assert step.llm_meta.prompt_tokens == 15
        assert step.llm_meta.completion_tokens == 25
        assert step.llm_meta.total_tokens == 40
        assert step.llm_meta.finish_reason == "stop"

        _cleanup_session()

    def test_no_llm_meta_when_result_has_no_model(self):
        """结果对象没有 model 属性时 llm_meta 应为 None。"""

        @llm_node(name="no_meta_llm")
        async def my_func() -> dict:
            return {"text": "plain dict result"}

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.llm_meta is None

        _cleanup_session()

    def test_no_llm_meta_when_result_is_none(self):
        """返回 None 时 llm_meta 应为 None。"""

        @llm_node(name="none_result_llm")
        async def my_func():
            return None

        session = _make_session()
        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.llm_meta is None

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: LangSmith integration
# ---------------------------------------------------------------------------


class TestLLMNodeLangSmith:
    """LangSmith 上报行为。"""

    def test_sets_langsmith_run_id_when_client_present(self):
        """有 LangSmith client 时应设置 langsmith_run_id 和 langsmith_run_url。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(
            _langsmith=langsmith,
            _langsmith_parent_run_id="parent-run-1",
        )

        @llm_node(name="langsmith_llm")
        async def my_func() -> _FakeLLMResult:
            return _FakeLLMResult()

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.langsmith_run_id is not None
        assert step.langsmith_run_url is not None

        # Verify LangSmith client was called correctly
        langsmith.start_run.assert_called_once_with(
            name="langsmith_llm",
            run_type="llm",
            inputs={"function": "my_func"},
            parent_run_id="parent-run-1",
        )
        langsmith.end_run.assert_called_once()

        _cleanup_session()

    def test_langsmith_end_run_receives_output_dict(self):
        """LangSmith end_run 应接收包含 content 和 usage 的输出。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(_langsmith=langsmith)

        @llm_node(name="ls_output_llm")
        async def my_func() -> _FakeLLMResult:
            return _FakeLLMResult(content="test output")

        asyncio.get_event_loop().run_until_complete(my_func())

        end_call = langsmith.end_run.call_args
        outputs = end_call[1].get("outputs", end_call[0][1] if len(end_call[0]) > 1 else None)
        # The decorator passes outputs= as keyword arg
        if outputs is None:
            outputs = end_call.kwargs.get("outputs")
        assert outputs is not None
        assert "content" in outputs
        assert outputs["content"] == "test output"

        _cleanup_session()

    def test_no_langsmith_calls_when_no_client(self):
        """无 LangSmith client 时不应报错。"""
        session = _make_session()

        @llm_node(name="no_ls_llm")
        async def my_func() -> str:
            return "result"

        asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.langsmith_run_id is None
        assert step.langsmith_run_url is None

        _cleanup_session()

    def test_langsmith_failure_does_not_break_step(self):
        """LangSmith start_run 抛异常时，步骤仍应正常完成。"""
        langsmith = MagicMock()
        langsmith.start_run.side_effect = RuntimeError("LangSmith down")
        session = _make_session(_langsmith=langsmith)

        @llm_node(name="ls_fail_llm")
        async def my_func() -> str:
            return "result"

        # LangSmith failure is swallowed, function executes normally
        result = asyncio.get_event_loop().run_until_complete(my_func())
        assert result == "result"

        # Step should still exist and be in success state
        step = session.trace.steps[0]
        assert step.status == "success"
        assert step.langsmith_run_id is None  # LangSmith failed, no run_id

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------


class TestLLMNodeError:
    """异常处理行为。"""

    def test_exception_sets_failed_status_and_reraises(self):
        """函数抛异常时 step.status='failed'，异常 re-raised。"""

        @llm_node(name="fail_llm")
        async def my_func() -> None:
            raise ValueError("LLM call failed")

        session = _make_session()

        with pytest.raises(ValueError, match="LLM call failed"):
            asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.status == "failed"
        assert "LLM call failed" in step.error

        _cleanup_session()

    def test_error_calls_langsmith_end_run_with_error(self):
        """异常时应调用 LangSmith end_run 并传递 error。"""
        langsmith = _make_langsmith_mock()
        session = _make_session(_langsmith=langsmith)

        @llm_node(name="err_ls_llm")
        async def my_func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            asyncio.get_event_loop().run_until_complete(my_func())

        step = session.trace.steps[0]
        assert step.status == "failed"

        # LangSmith end_run should have been called with error
        langsmith.end_run.assert_called_once()
        end_call = langsmith.end_run.call_args
        assert "boom" in str(end_call)

        _cleanup_session()


# ---------------------------------------------------------------------------
# Test: functools.wraps
# ---------------------------------------------------------------------------


class TestLLMNodeFunctoolsWraps:
    """装饰器应保留被装饰函数的元数据。"""

    def test_preserves_name(self):
        @llm_node(name="wrapped")
        async def my_llm_func():
            """My LLM function."""
            pass

        assert my_llm_func.__name__ == "my_llm_func"

    def test_preserves_doc(self):
        @llm_node(name="wrapped")
        async def my_llm_func():
            """My LLM function."""
            pass

        assert my_llm_func.__doc__ == "My LLM function."
