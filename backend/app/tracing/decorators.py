"""Trace V2 装饰器 — @traceable_node 提供 AOP 风格的追踪能力。"""

import functools
import inspect
import logging
from datetime import UTC, datetime
from typing import Callable

from app.tracing.context import (
    clear_current_trace,
    get_current_step_id,
    get_current_trace,
    reset_current_step_id,
    set_current_step_id,
    set_current_trace,
)
from app.tracing.models import LLMMeta, NodeType
from app.tracing.session import TraceSession

logger = logging.getLogger(__name__)

# 输入序列化时始终排除的参数名
_EXCLUDED_PARAMS = {"settings", "self", "cls"}

# 参数名中包含这些子串视为敏感参数
_SENSITIVE_PATTERNS = {"api_key", "secret", "password", "token"}

# 字符串截断阈值
_MAX_STRING_LEN = 2000


def _is_sensitive_param(name: str) -> bool:
    """判断参数名是否为敏感参数（应排除不记录）。"""
    if name in _EXCLUDED_PARAMS:
        return True
    return any(p in name.lower() for p in _SENSITIVE_PATTERNS)


def _truncate_strings(data, max_len: int = _MAX_STRING_LEN):
    """递归截断所有超过 max_len 的字符串值。"""
    if isinstance(data, str):
        if len(data) > max_len:
            return data[:max_len] + "[TRUNCATED]"
        return data
    if isinstance(data, dict):
        return {k: _truncate_strings(v, max_len) for k, v in data.items()}
    if isinstance(data, list):
        return [_truncate_strings(v, max_len) for v in data]
    return data


def _serialize_input(
    func: Callable,
    args: tuple,
    kwargs: dict,
    serializer: Callable | None = None,
) -> dict:
    """将函数输入参数序列化为可记录的 dict。

    Args:
        func: 被装饰的函数，用于提取参数签名。
        args: 位置参数。
        kwargs: 关键字参数。
        serializer: 可选的自定义序列化器，签名为 (args, kwargs) -> dict。

    Returns:
        序列化后的输入字典。
    """
    if serializer:
        return _truncate_strings(serializer(args, kwargs))

    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
    except (ValueError, TypeError):
        return {}

    result: dict = {}
    for i, arg in enumerate(args):
        if i < len(params) and not _is_sensitive_param(params[i]):
            result[params[i]] = (
                _truncate_strings(arg) if isinstance(arg, str) else arg
            )
    for name, value in kwargs.items():
        if not _is_sensitive_param(name):
            result[name] = (
                _truncate_strings(value) if isinstance(value, str) else value
            )
    return _truncate_strings(result)


def _serialize_output(result, serializer: Callable | None = None) -> dict:
    """将函数输出序列化为可记录的 dict。

    Args:
        result: 函数返回值。
        serializer: 可选的自定义序列化器，签名为 (result) -> dict。

    Returns:
        序列化后的输出字典。
    """
    if serializer:
        return _truncate_strings(serializer(result))
    if isinstance(result, dict):
        return _truncate_strings(result)
    return _truncate_strings({"result": str(result)})


def _elapsed_ms(started_at: str) -> float:
    """根据 started_at ISO 字符串计算已流逝的毫秒数。"""
    if not started_at:
        return 0.0
    try:
        start = datetime.fromisoformat(started_at)
        return (datetime.now(UTC) - start).total_seconds() * 1000
    except (ValueError, TypeError):
        return 0.0


def traceable_node(
    name: str,
    node_type: NodeType = NodeType.CUSTOM,
    *,
    capture_input: bool = True,
    capture_output: bool = True,
    input_serializer: Callable | None = None,
    output_serializer: Callable | None = None,
):
    """将异步函数标记为可追踪节点。

    装饰器会自动创建 FlowStep 并注册到当前活跃的 TraceSession 中。
    无活跃 session 时为 NoOp，不影响函数执行。

    Args:
        name: 步骤名称，用于标识追踪节点（如 "llm_generate_script"）。
        node_type: 节点类型分类。
        capture_input: 是否捕获输入参数。
        capture_output: 是否捕获输出。
        input_serializer: 自定义输入序列化器，签名为 (args, kwargs) -> dict。
        output_serializer: 自定义输出序列化器，签名为 (result) -> dict。

    Returns:
        装饰器函数。
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # NoOp: 无活跃 session 时直接透传
            session = get_current_trace()
            if session is None:
                return await func(*args, **kwargs)

            # 获取父步骤 ID，创建新步骤
            parent_id = get_current_step_id()
            step = session.create_step(name, node_type, parent_id)

            # 设置当前步骤 ID，支持嵌套
            token = set_current_step_id(step.step_id)

            try:
                # 捕获输入
                if capture_input:
                    step.input_data = _serialize_input(
                        func, args, kwargs, input_serializer,
                    )

                # 执行被装饰函数
                result = await func(*args, **kwargs)

                # 捕获输出
                if capture_output:
                    step.output_data = _serialize_output(
                        result, output_serializer,
                    )

                step.status = "success"
                return result

            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                raise

            finally:
                # 计算耗时并恢复父步骤上下文
                step.duration_ms = _elapsed_ms(step.started_at)
                reset_current_step_id(token)

        return wrapper

    return decorator


def get_trace_v2_store(settings):
    """Lazy import to avoid circular dependency."""
    from app.tracing.store import TraceStore
    return TraceStore(settings.trace_dir, settings.trace_retention_days)


def with_trace(
    flow_type: str,
    *,
    error_map: dict[type[Exception], tuple[int, str]] | None = None,
):
    """路由级 trace 装饰器，替代手动 try/except/finally 编排。"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            from app.schemas.common import ApiResponse, ErrorCode as EC
            from app.logging_config import request_id_ctx

            settings = kwargs.get("settings")
            response = kwargs.get("response")
            request_id = request_id_ctx.get("")

            # NoOp: skip all tracing when not enabled
            if not settings or not getattr(settings, "trace_enabled", False):
                return await func(*args, **kwargs)

            session = TraceSession(flow_type, request_id, settings)
            set_current_trace(session)

            try:
                result = await func(*args, **kwargs)
                session.finish("success")
                return result
            except Exception as e:
                session.finish("failed", error=str(e))
                for exc_type, (code, msg) in (error_map or {}).items():
                    if isinstance(e, exc_type):
                        return ApiResponse(code=code, message=msg, data=None)
                return ApiResponse(code=EC.INTERNAL_ERROR, message=str(e), data=None)
            finally:
                try:
                    store = get_trace_v2_store(settings)
                    store.save(session.trace)
                except Exception:
                    logger.warning("Failed to save trace", exc_info=True)
                if response:
                    try:
                        response.headers["x-trace-id"] = session.trace.trace_id
                    except Exception:
                        pass
                clear_current_trace()

        return wrapper

    return decorator


def llm_node(name: str, *, capture_prompt: bool = True, capture_response: bool = True):
    """LLM 节点专用装饰器。自动创建 FlowStep + 上报 LangSmith + 提取 LLMMeta。

    与 @traceable_node 独立实现（非包装），内置 LangSmith 上报和 LLM 元数据提取。

    Args:
        name: 步骤名称。
        capture_prompt: 是否捕获输入参数。
        capture_response: 是否捕获输出。

    Returns:
        装饰器函数。
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            session = get_current_trace()
            if session is None:
                return await func(*args, **kwargs)

            parent_id = get_current_step_id()
            step = session.create_step(name, NodeType.LLM, parent_id)
            token = set_current_step_id(step.step_id)

            # LangSmith start (失败不影响主流程)
            langsmith_client = getattr(session, '_langsmith', None)
            parent_run_id = getattr(session, '_langsmith_parent_run_id', None)
            run_result = None
            if langsmith_client:
                try:
                    run_result = langsmith_client.start_run(
                        name=name,
                        run_type="llm",
                        inputs={"function": func.__name__},
                        parent_run_id=parent_run_id,
                    )
                except Exception:
                    logger.warning("LangSmith start_run failed", exc_info=True)

            try:
                if capture_prompt:
                    step.input_data = _serialize_input(func, args, kwargs, None)
                result = await func(*args, **kwargs)
                if capture_response:
                    step.output_data = _serialize_output(result, None)

                # Extract LLMMeta from result if it has usage attributes
                if result is not None and hasattr(result, 'model'):
                    step.llm_meta = LLMMeta(
                        model=getattr(result, 'model', ''),
                        prompt_tokens=getattr(result, 'prompt_tokens', 0),
                        completion_tokens=getattr(result, 'completion_tokens', 0),
                        total_tokens=getattr(result, 'total_tokens', 0),
                        finish_reason=getattr(result, 'finish_reason', None),
                    )

                if run_result:
                    step.langsmith_run_id = run_result.run_id
                    step.langsmith_run_url = run_result.run_url

                # LangSmith end
                if langsmith_client and run_result:
                    output_dict = {}
                    if hasattr(result, 'content'):
                        output_dict["content"] = result.content[:500]
                    if hasattr(result, 'usage'):
                        output_dict["usage"] = result.usage
                    langsmith_client.end_run(run_result.run_id, outputs=output_dict)

                step.status = "success"
                return result
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                if langsmith_client and run_result:
                    langsmith_client.end_run(run_result.run_id, error=str(e))
                raise
            finally:
                step.duration_ms = _elapsed_ms(step.started_at)
                reset_current_step_id(token)

        return wrapper

    return decorator


def image_gen_node(name: str, *, capture_prompt: bool = True):
    """图像生成节点装饰器。LangSmith run_type="tool"，不记录 base64 数据。

    Args:
        name: 步骤名称。
        capture_prompt: 是否捕获输入参数。

    Returns:
        装饰器函数。
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            session = get_current_trace()
            if session is None:
                return await func(*args, **kwargs)

            parent_id = get_current_step_id()
            step = session.create_step(name, NodeType.IMAGE_GEN, parent_id)
            token = set_current_step_id(step.step_id)

            langsmith_client = getattr(session, '_langsmith', None)
            parent_run_id = getattr(session, '_langsmith_parent_run_id', None)
            run_result = None
            if langsmith_client:
                try:
                    run_result = langsmith_client.start_run(
                        name=name,
                        run_type="tool",
                        inputs={"function": func.__name__},
                        parent_run_id=parent_run_id,
                    )
                except Exception:
                    logger.warning("LangSmith start_run failed", exc_info=True)

            try:
                if capture_prompt:
                    step.input_data = _serialize_input(func, args, kwargs, None)
                result = await func(*args, **kwargs)
                # For image gen, capture metadata not base64
                if isinstance(result, str) and len(result) > 200:
                    step.output_data = {"result_length": len(result), "type": "base64_image"}
                else:
                    step.output_data = _serialize_output(result, None)

                if run_result:
                    step.langsmith_run_id = run_result.run_id
                    step.langsmith_run_url = run_result.run_url

                if langsmith_client and run_result:
                    langsmith_client.end_run(run_result.run_id, outputs={"status": "success"})

                step.status = "success"
                return result
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                if langsmith_client and run_result:
                    langsmith_client.end_run(run_result.run_id, error=str(e))
                raise
            finally:
                step.duration_ms = _elapsed_ms(step.started_at)
                reset_current_step_id(token)

        return wrapper

    return decorator
