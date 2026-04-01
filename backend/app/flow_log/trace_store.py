"""TraceStore — JSONL 文件存储、查询、自动清理。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.flow_log.trace import FlowTrace

logger = logging.getLogger(__name__)


class TraceStore:
    """JSONL 格式的 trace 文件存储，追加写入，并发安全。"""

    def __init__(self, trace_dir: str, retention_days: int = 7) -> None:
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days

    def save(self, trace: FlowTrace) -> None:
        """追加写入当天 trace 文件（JSONL 格式，并发安全）。"""
        try:
            date_str = trace.created_at[:10]
            file_path = self.trace_dir / f"{date_str}.jsonl"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(trace.model_dump_json() + "\n")
        except Exception:
            logger.warning("Failed to save trace %s", trace.trace_id, exc_info=True)

    def query(self, date: str | None = None, limit: int = 20) -> list[FlowTrace]:
        """查询指定日期的 trace 记录，返回最新的 N 条。"""
        date_str = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_path = self.trace_dir / f"{date_str}.jsonl"
        if not file_path.exists():
            return []
        traces: list[FlowTrace] = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        traces.append(FlowTrace.model_validate_json(line))
        except Exception:
            logger.warning("Failed to read trace file %s", file_path, exc_info=True)
            return []
        return list(reversed(traces))[:limit]

    def cleanup(self, retention_days: int | None = None) -> int:
        """删除超过 retention_days 的文件。返回删除的文件数。"""
        days = retention_days if retention_days is not None else self.retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        removed = 0
        for file_path in self.trace_dir.glob("*.jsonl"):
            try:
                date_str = file_path.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if file_date < cutoff:
                    file_path.unlink()
                    removed += 1
            except (ValueError, OSError):
                continue
        if removed > 0:
            logger.info("Cleaned up %d expired trace files (retention=%d days)", removed, days)
        return removed
