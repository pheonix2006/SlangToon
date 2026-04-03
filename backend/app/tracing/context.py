"""Trace V2 ContextVars — trace session 和 step_id 的异步上下文传播。"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.tracing.session import TraceSession

_current_trace: ContextVar[TraceSession | None] = ContextVar(
    "current_trace", default=None,
)
_current_step_id: ContextVar[str | None] = ContextVar(
    "current_step_id", default=None,
)


def get_current_trace() -> TraceSession | None:
    """获取当前上下文中的 trace session。"""
    return _current_trace.get()


def set_current_trace(session: TraceSession) -> None:
    """设置当前上下文的 trace session。"""
    _current_trace.set(session)


def clear_current_trace() -> None:
    """清除当前上下文的 trace session（重置为 None）。"""
    _current_trace.set(None)


def get_current_step_id() -> str | None:
    """获取当前上下文中的步骤 ID。"""
    return _current_step_id.get()


def set_current_step_id(step_id: str | None) -> Token:  # type: ignore[type-arg]
    """设置当前步骤 ID，返回 Token 用于后续 reset。"""
    return _current_step_id.set(step_id)


def reset_current_step_id(token: Token) -> None:  # type: ignore[type-arg]
    """通过 Token 恢复到之前的步骤 ID。"""
    _current_step_id.reset(token)
