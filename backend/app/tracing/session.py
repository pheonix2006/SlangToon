"""TraceSession — 管理 FlowTrace 生命周期，创建 DAG 步骤。"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from app.tracing.models import FlowStep, FlowTrace, NodeType

logger = logging.getLogger(__name__)


class TraceSession:
    """追踪会话：一次完整 API 调用的运行时上下文。

    创建 FlowTrace 并提供 create_step / finish 方法构建 DAG 步骤树。
    parent_id 由调用方（装饰器）传入，不存储在 session 状态中，
    确保 asyncio 并行安全。
    """

    def __init__(self, flow_type: str, request_id: str, settings=None) -> None:
        self.trace = FlowTrace(
            trace_id=f"t-{uuid4().hex[:12]}",
            request_id=request_id,
            flow_type=flow_type,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._started_at = datetime.now(UTC)
        self._langsmith = None
        self._langsmith_parent_run_id = None
        if settings and getattr(settings, "langsmith_enabled", False):
            from app.tracing.langsmith_client import LangSmithClient
            self._langsmith = LangSmithClient(
                enabled=settings.langsmith_enabled,
                api_key=settings.langsmith_api_key,
                project=settings.langsmith_project,
                endpoint=settings.langsmith_endpoint,
            )

    def create_step(
        self,
        name: str,
        node_type: NodeType,
        parent_id: str | None = None,
    ) -> FlowStep:
        """创建一个流程步骤并追加到 trace.steps。

        Args:
            name: 步骤名称（如 "llm_generate_script"）。
            node_type: 节点类型（LLM / IMAGE_GEN / PROMPT / IO / CUSTOM）。
            parent_id: 父步骤 ID，为 None 时成为根步骤。

        Returns:
            新创建的 FlowStep 实例。
        """
        step = FlowStep(
            step_id=f"s-{uuid4().hex[:8]}",
            name=name,
            node_type=node_type,
            parent_id=parent_id,
            started_at=datetime.now(UTC).isoformat(),
        )
        self.trace.steps.append(step)

        if parent_id:
            parent = self._find_step(parent_id)
            if parent:
                parent.children_ids.append(step.step_id)
        else:
            self.trace.root_step_id = step.step_id

        return step

    def finish(self, status: str, error: str | None = None) -> None:
        """结束追踪会话，设置最终状态和总耗时。

        Args:
            status: 最终状态（"success" / "failed" 等）。
            error: 错误信息，仅在失败时提供。
        """
        self.trace.status = status
        elapsed = datetime.now(UTC) - self._started_at
        self.trace.total_duration_ms = elapsed.total_seconds() * 1000
        if error:
            self.trace.error = error

    def _find_step(self, step_id: str) -> FlowStep | None:
        """按 step_id 查找步骤。"""
        return next((s for s in self.trace.steps if s.step_id == step_id), None)
