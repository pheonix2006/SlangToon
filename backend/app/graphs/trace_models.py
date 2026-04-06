"""Lightweight trace data models for local storage."""

from pydantic import BaseModel, Field


class NodeRecord(BaseModel):
    """单个节点的执行记录。"""

    name: str
    output: dict | None = None
    timestamp: str = ""
    duration_ms: float = 0


class TraceRecord(BaseModel):
    """一次 Graph 执行的完整追踪记录。"""

    trace_id: str
    flow_type: str = ""  # "script" | "comic"
    request_id: str = ""
    nodes: list[NodeRecord] = Field(default_factory=list)
    status: str = "running"
    created_at: str = ""
    error: str | None = None
