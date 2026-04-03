"""LangSmith SDK 封装 — 两阶段 start_run/end_run，所有失败降级为 warning 日志。"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    run_id: str
    run_url: str


class LangSmithClient:
    def __init__(self, enabled: bool, api_key: str, project: str, endpoint: str):
        self.enabled = enabled
        self.project_name = project
        self._client = None
        if enabled:
            try:
                import langsmith

                self._client = langsmith.Client(api_key=api_key, api_url=endpoint)
            except Exception:
                logger.warning("Failed to initialize LangSmith client", exc_info=True)

    def start_run(
        self,
        name: str,
        run_type: str,
        inputs: dict,
        parent_run_id: str | None = None,
        extra: dict | None = None,
    ) -> RunResult | None:
        if not self.enabled or not self._client:
            return None
        run_id = str(uuid4())
        try:
            self._client.create_run(
                id=run_id,
                name=name,
                run_type=run_type,
                inputs=inputs,
                parent_run_id=parent_run_id,
                extra=extra,
            )
            return RunResult(
                run_id=run_id,
                run_url=f"https://smith.langchain.com/o/default/runs/{run_id}",
            )
        except Exception:
            logger.warning("LangSmith start_run failed", exc_info=True)
            return None

    def end_run(
        self,
        run_id: str,
        outputs: dict | None = None,
        error: str | None = None,
    ) -> None:
        if not self.enabled or not self._client:
            return
        try:
            self._client.update_run(
                run_id,
                outputs=outputs or {},
                error=error,
                end_time=datetime.now(UTC).isoformat(),
            )
        except Exception:
            logger.warning("LangSmith end_run failed", exc_info=True)
