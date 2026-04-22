"""Tests for trace_models — lightweight trace data models."""

from app.graphs.trace_models import NodeRecord, TraceRecord


def test_node_record_creation():
    node = NodeRecord(name="script_node", output={"slang": "test"}, timestamp="2026-04-05T10:00:00Z")
    assert node.name == "script_node"
    assert node.output["slang"] == "test"


def test_trace_record_creation():
    record = TraceRecord(
        trace_id="t-abc123",
        flow_type="script",
        nodes=[NodeRecord(name="script_node")],
        status="success",
    )
    assert record.trace_id == "t-abc123"
    assert len(record.nodes) == 1
    assert record.status == "success"


def test_trace_record_serialization():
    record = TraceRecord(trace_id="t-xyz", flow_type="comic", status="success")
    json_str = record.model_dump_json()
    restored = TraceRecord.model_validate_json(json_str)
    assert restored.trace_id == record.trace_id
    assert restored.flow_type == record.flow_type


def test_trace_record_with_error():
    record = TraceRecord(trace_id="t-err", flow_type="script", status="failed", error="timeout")
    assert record.error == "timeout"
    assert record.status == "failed"


class TestNodeRecordReasoningContent:
    def test_default_none(self):
        record = NodeRecord(name="test_node")
        assert record.reasoning_content is None

    def test_with_reasoning(self):
        record = NodeRecord(name="script_node", reasoning_content="I'm thinking about...")
        assert record.reasoning_content == "I'm thinking about..."

    def test_serialization_includes_reasoning(self):
        record = NodeRecord(name="n", reasoning_content="think")
        d = record.model_dump()
        assert d["reasoning_content"] == "think"

    def test_serialization_excludes_none(self):
        record = NodeRecord(name="n")
        d = record.model_dump(exclude_none=True)
        assert "reasoning_content" not in d
