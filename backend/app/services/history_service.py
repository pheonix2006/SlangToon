import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class HistoryService:
    def __init__(self, history_file: str, max_records: int = 1000):
        self.history_file = Path(history_file)
        self.max_records = max_records

    def _load(self) -> list[dict]:
        if not self.history_file.exists():
            return []
        return json.loads(self.history_file.read_text(encoding="utf-8"))

    def _save(self, records: list[dict]):
        self.history_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, item: dict) -> str:
        records = self._load()
        item["id"] = item.get("id", str(uuid.uuid4()))
        item["created_at"] = item.get("created_at", datetime.now(timezone.utc).isoformat())
        records.insert(0, item)
        if len(records) > self.max_records:
            records = records[:self.max_records]
        self._save(records)
        return item["id"]

    def get_page(self, page: int = 1, page_size: int = 20) -> dict:
        records = self._load()
        total = len(records)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        items = records[start:start + page_size]
        return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": total_pages}
