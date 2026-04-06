"""俚语黑名单管理 — 防止重复生成相同俚语。"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class SlangBlacklist:
    """管理已生成俚语的黑名单，防止重复。"""

    def __init__(self, file_path: str, max_entries: int = 50) -> None:
        self.file_path = Path(file_path)
        self.max_entries = max_entries

    def load(self) -> list[str]:
        """从 JSON 文件加载黑名单条目列表。"""
        if not self.file_path.exists():
            return []
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return data.get("entries", [])
        except (json.JSONDecodeError, KeyError, AttributeError) as exc:
            logger.warning("黑名单文件损坏，已重置: %s (%s)", self.file_path, exc)
            return []

    def save(self, entries: list[str]) -> None:
        """将条目列表持久化到 JSON 文件。"""
        data = {
            "entries": entries,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, slang: str) -> None:
        """添加新 slang 到黑名单（去重+截断到 max_entries）。"""
        entries = self.load()
        entries = [e for e in entries if e != slang]
        entries.insert(0, slang)
        if len(entries) > self.max_entries:
            entries = entries[: self.max_entries]
        self.save(entries)

    def get_recent(self, limit: int = 50) -> list[str]:
        """获取最近 N 条黑名单条目。"""
        entries = self.load()
        return entries[:limit]

    def contains(self, slang: str) -> bool:
        """快速查询某 slang 是否已在黑名单中。"""
        return slang in self.load()
