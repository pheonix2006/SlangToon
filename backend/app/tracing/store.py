"""TraceStore V2 — JSONL 文件存储、查询、过滤、trace_id 查找、自动清理。"""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.tracing.models import FlowTrace

logger = logging.getLogger(__name__)


class TraceStore:
    """JSONL 格式的 trace 文件存储，支持按日期/flow_type/status 查询和 trace_id 精确查找。"""

    def __init__(self, trace_dir: str, retention_days: int = 7) -> None:
        self._trace_dir = Path(trace_dir)
        self._retention_days = retention_days
        self._trace_dir.mkdir(parents=True, exist_ok=True)

    def save(self, trace: FlowTrace) -> None:
        """追加写入当天 trace 文件（JSONL 格式）。"""
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = self._trace_dir / f"{date_str}.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(trace.model_dump_json() + "\n")

    def query(
        self,
        date: str | None = None,
        limit: int = 20,
        flow_type: str | None = None,
        status: str | None = None,
    ) -> list[FlowTrace]:
        """查询指定日期的 trace 记录，支持按 flow_type 和 status 过滤，返回最新的 N 条。"""
        if date is None:
            date = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = self._trace_dir / f"{date}.jsonl"
        if not file_path.exists():
            return []

        traces: list[FlowTrace] = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    trace = FlowTrace.model_validate_json(line)
                except Exception:
                    continue
                if flow_type and trace.flow_type != flow_type:
                    continue
                if status and trace.status != status:
                    continue
                traces.append(trace)

        return list(reversed(traces))[:limit]

    def get_by_trace_id(self, trace_id: str, scan_days: int = 7) -> FlowTrace | None:
        """在最近 scan_days 天内查找指定 trace_id 的记录。"""
        now = datetime.now(UTC)
        for i in range(scan_days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            file_path = self._trace_dir / f"{date}.jsonl"
            if not file_path.exists():
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        trace = FlowTrace.model_validate_json(line)
                        if trace.trace_id == trace_id:
                            return trace
                    except Exception:
                        continue
        return None

    def cleanup(self, retention_days: int | None = None) -> int:
        """删除超过 retention_days 的文件。返回删除的文件数。"""
        days = retention_days or self._retention_days
        cutoff = datetime.now(UTC) - timedelta(days=days)
        deleted = 0
        for f in self._trace_dir.glob("*.jsonl"):
            try:
                file_date = datetime.strptime(f.stem, "%Y-%m-%d").replace(tzinfo=UTC)
                if file_date < cutoff:
                    f.unlink()
                    deleted += 1
            except ValueError:
                continue
        return deleted
