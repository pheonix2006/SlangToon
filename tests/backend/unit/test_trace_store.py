"""TraceStore V2 单元测试 — JSONL 存储、查询、过滤、trace_id 查找、清理。"""

import json
from datetime import UTC, datetime

import pytest

from app.tracing.models import FlowTrace
from app.tracing.store import TraceStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace(
    trace_id: str = "t-001",
    flow_type: str = "script",
    status: str = "success",
    created_at: str | None = None,
) -> FlowTrace:
    """快速创建 FlowTrace 实例。"""
    return FlowTrace(
        trace_id=trace_id,
        request_id=f"req-{trace_id}",
        flow_type=flow_type,
        status=status,
        created_at=created_at or datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# TestTraceStoreSave
# ---------------------------------------------------------------------------


class TestTraceStoreSave:
    """save() 相关测试。"""

    def test_save_creates_jsonl_file(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        trace = _make_trace("t-001")
        store.save(trace)

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = tmp_path / "traces" / f"{date_str}.jsonl"
        assert file_path.exists()

    def test_save_appends_multiple_traces_to_same_file(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-001"))
        store.save(_make_trace("t-002"))
        store.save(_make_trace("t-003"))

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = tmp_path / "traces" / f"{date_str}.jsonl"
        lines = file_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

    def test_each_line_is_valid_json_with_correct_trace_id(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-alpha"))
        store.save(_make_trace("t-beta"))

        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        file_path = tmp_path / "traces" / f"{date_str}.jsonl"
        lines = file_path.read_text(encoding="utf-8").strip().split("\n")

        ids = [json.loads(line)["trace_id"] for line in lines]
        assert ids == ["t-alpha", "t-beta"]


# ---------------------------------------------------------------------------
# TestTraceStoreQuery
# ---------------------------------------------------------------------------


class TestTraceStoreQuery:
    """query() 相关测试。"""

    def test_query_returns_saved_traces(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-001"))
        store.save(_make_trace("t-002"))

        results = store.query()
        assert len(results) == 2
        result_ids = {t.trace_id for t in results}
        assert result_ids == {"t-001", "t-002"}

    def test_query_respects_limit(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        for i in range(5):
            store.save(_make_trace(f"t-{i:03d}"))

        results = store.query(limit=3)
        assert len(results) == 3

    def test_query_returns_newest_first(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-first"))
        store.save(_make_trace("t-second"))
        store.save(_make_trace("t-third"))

        results = store.query(limit=10)
        assert results[0].trace_id == "t-third"
        assert results[1].trace_id == "t-second"
        assert results[2].trace_id == "t-first"

    def test_query_returns_empty_for_missing_date(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        results = store.query(date="2099-12-31")
        assert results == []

    def test_query_filters_by_flow_type(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-1", flow_type="script"))
        store.save(_make_trace("t-2", flow_type="comic"))
        store.save(_make_trace("t-3", flow_type="script"))

        results = store.query(flow_type="script")
        assert len(results) == 2
        assert all(t.flow_type == "script" for t in results)

    def test_query_filters_by_status(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-1", status="success"))
        store.save(_make_trace("t-2", status="failed"))
        store.save(_make_trace("t-3", status="success"))

        results = store.query(status="failed")
        assert len(results) == 1
        assert results[0].trace_id == "t-2"

    def test_query_filters_by_both_flow_type_and_status(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-1", flow_type="script", status="success"))
        store.save(_make_trace("t-2", flow_type="script", status="failed"))
        store.save(_make_trace("t-3", flow_type="comic", status="failed"))
        store.save(_make_trace("t-4", flow_type="script", status="success"))

        results = store.query(flow_type="script", status="success")
        assert len(results) == 2
        assert all(t.flow_type == "script" and t.status == "success" for t in results)


# ---------------------------------------------------------------------------
# TestTraceStoreGetByTraceId
# ---------------------------------------------------------------------------


class TestTraceStoreGetByTraceId:
    """get_by_trace_id() 相关测试。"""

    def test_find_existing_trace_by_id(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-target"))
        store.save(_make_trace("t-other"))

        result = store.get_by_trace_id("t-target")
        assert result is not None
        assert result.trace_id == "t-target"

    def test_not_found_returns_none(self, tmp_path):
        store = TraceStore(str(tmp_path / "traces"))
        store.save(_make_trace("t-001"))

        result = store.get_by_trace_id("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# TestTraceStoreCleanup
# ---------------------------------------------------------------------------


class TestTraceStoreCleanup:
    """cleanup() 相关测试。"""

    def test_removes_old_files(self, tmp_path):
        trace_dir = tmp_path / "traces"
        trace_dir.mkdir()
        store = TraceStore(str(trace_dir), retention_days=7)

        # 创建一个过期的旧文件
        old_file = trace_dir / "2026-03-20.jsonl"
        old_file.write_text('{"old": true}\n', encoding="utf-8")

        # 创建一个最近的文件
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        recent_file = trace_dir / f"{today_str}.jsonl"
        recent_file.write_text('{"recent": true}\n', encoding="utf-8")

        deleted = store.cleanup()
        assert deleted == 1
        assert not old_file.exists()
        assert recent_file.exists()

    def test_keeps_recent_files(self, tmp_path):
        trace_dir = tmp_path / "traces"
        trace_dir.mkdir()
        store = TraceStore(str(trace_dir), retention_days=7)

        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        today_file = trace_dir / f"{today_str}.jsonl"
        today_file.write_text('{"today": true}\n', encoding="utf-8")

        deleted = store.cleanup()
        assert deleted == 0
        assert today_file.exists()
