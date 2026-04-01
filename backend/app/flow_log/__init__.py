"""FlowTrace — 全流程调用链追踪。"""

from app.flow_log.trace import FlowSession, NoOpSession, _current_trace, get_current_trace

__all__ = ["FlowSession", "NoOpSession", "get_current_trace", "set_current_trace"]


def set_current_trace(session: FlowSession | NoOpSession) -> None:
    """设置当前请求的 trace session（供路由层调用）。"""
    _current_trace.set(session)
