"""Tests for trace_store — JSONL trace storage."""

import datetime

from app.graphs.trace_store import TraceStore
from app.graphs.trace_models import TraceRecord, NodeRecord


def test_save_and_query(tmp_path):
    store = TraceStore(str(tmp_path / "traces"))
    record = TraceRecord(
        trace_id="t-001",
        flow_type="script",
        nodes=[NodeRecord(name="script_node", output={"slang": "test"})],
        status="success",
        created_at="2026-04-05T10:00:00Z",
    )
    store.save(record)
    results = store.query()
    assert len(results) == 1
    assert results[0].trace_id == "t-001"


def test_get_by_trace_id(tmp_path):
    store = TraceStore(str(tmp_path / "traces"))
    record = TraceRecord(trace_id="t-002", flow_type="comic", status="success")
    store.save(record)
    found = store.get_by_trace_id("t-002")
    assert found is not None
    assert found.flow_type == "comic"


def test_get_by_trace_id_not_found(tmp_path):
    store = TraceStore(str(tmp_path / "traces"))
    assert store.get_by_trace_id("nonexistent") is None


def test_query_with_filter(tmp_path):
    store = TraceStore(str(tmp_path / "traces"))
    store.save(TraceRecord(trace_id="t-003", flow_type="script", status="success"))
    store.save(TraceRecord(trace_id="t-004", flow_type="comic", status="failed"))

    script_only = store.query(flow_type="script")
    assert len(script_only) == 1
    assert script_only[0].flow_type == "script"

    failed_only = store.query(status="failed")
    assert len(failed_only) == 1
    assert failed_only[0].status == "failed"


def test_cleanup_removes_old_files(tmp_path):
    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()
    old_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    (traces_dir / f"{old_date}.jsonl").write_text('{"test": true}\n')

    store = TraceStore(str(traces_dir), retention_days=7)
    deleted = store.cleanup()
    assert deleted == 1
    assert not (traces_dir / f"{old_date}.jsonl").exists()


def test_cleanup_keeps_recent_files(tmp_path):
    store = TraceStore(str(tmp_path / "traces"))
    record = TraceRecord(trace_id="t-recent", flow_type="script", status="success")
    store.save(record)

    deleted = store.cleanup(retention_days=7)
    assert deleted == 0
    found = store.get_by_trace_id("t-recent")
    assert found is not None
