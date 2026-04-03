"""Trace V2 数据模型 — 节点类型、LLM 元数据、流程步骤、流程追踪。"""

from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """追踪节点的类型分类。"""

    LLM = "llm"
    IMAGE_GEN = "image_gen"
    PROMPT = "prompt"
    IO = "io"
    CUSTOM = "custom"


class LLMMeta(BaseModel):
    """LLM 调用元数据（token 用量、模型、参数等）。"""

    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    temperature: float | None = None
    finish_reason: str | None = None


class FlowStep(BaseModel):
    """流程中的单个步骤，支持 DAG 结构（parent_id / children_ids）。"""

    step_id: str
    name: str
    node_type: NodeType
    status: str = "running"
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    input_data: dict | None = None
    output_data: dict | None = None
    llm_meta: LLMMeta | None = None
    langsmith_run_id: str | None = None
    langsmith_run_url: str | None = None
    started_at: str = ""
    duration_ms: float = 0
    error: str | None = None


class FlowTrace(BaseModel):
    """一次完整 API 调用的追踪记录，包含 DAG 结构的步骤树。"""

    trace_id: str
    request_id: str
    flow_type: str  # 保持可扩展，不使用 Literal
    status: str = "running"
    created_at: str = ""
    total_duration_ms: float = 0
    steps: list[FlowStep] = Field(default_factory=list)
    root_step_id: str | None = None
    error: str | None = None
