"""Trace V2 数据模型单元测试。"""

import json

import pytest
from pydantic import ValidationError

from app.tracing.models import FlowStep, FlowTrace, LLMMeta, NodeType


# ── NodeType 枚举 ─────────────────────────────────────────────


class TestNodeType:
    """NodeType 枚举值与字符串转换。"""

    def test_enum_values(self):
        """所有枚举成员的值正确。"""
        assert NodeType.LLM == "llm"
        assert NodeType.IMAGE_GEN == "image_gen"
        assert NodeType.PROMPT == "prompt"
        assert NodeType.IO == "io"
        assert NodeType.CUSTOM == "custom"

    def test_string_conversion(self):
        """枚举可转为字符串，且值就是字符串。"""
        assert str(NodeType.LLM) == "NodeType.LLM"
        assert NodeType.LLM.value == "llm"

    def test_from_string(self):
        """可从字符串构造枚举。"""
        assert NodeType("llm") is NodeType.LLM
        assert NodeType("image_gen") is NodeType.IMAGE_GEN

    def test_invalid_string_raises(self):
        """无效字符串构造枚举抛出 ValueError。"""
        with pytest.raises(ValueError):
            NodeType("nonexistent")

    def test_member_count(self):
        """共 5 个枚举成员。"""
        assert len(NodeType) == 5


# ── LLMMeta ───────────────────────────────────────────────────


class TestLLMMeta:
    """LLM 调用元数据模型。"""

    def test_defaults(self):
        """所有字段都有合理默认值。"""
        meta = LLMMeta()
        assert meta.model == ""
        assert meta.prompt_tokens == 0
        assert meta.completion_tokens == 0
        assert meta.total_tokens == 0
        assert meta.temperature is None
        assert meta.finish_reason is None

    def test_full_construction(self):
        """完整构造并读取所有字段。"""
        meta = LLMMeta(
            model="glm-4.6v",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            temperature=0.9,
            finish_reason="stop",
        )
        assert meta.model == "glm-4.6v"
        assert meta.prompt_tokens == 100
        assert meta.completion_tokens == 50
        assert meta.total_tokens == 150
        assert meta.temperature == 0.9
        assert meta.finish_reason == "stop"

    def test_serialization_roundtrip(self):
        """序列化 → 反序列化保持一致。"""
        original = LLMMeta(
            model="qwen-v2",
            prompt_tokens=200,
            completion_tokens=80,
            total_tokens=280,
            temperature=0.7,
            finish_reason="length",
        )
        data = original.model_dump()
        restored = LLMMeta.model_validate(data)
        assert restored == original

    def test_json_roundtrip(self):
        """JSON 序列化 → 反序列化保持一致。"""
        original = LLMMeta(model="test", total_tokens=42)
        json_str = original.model_dump_json()
        restored = LLMMeta.model_validate_json(json_str)
        assert restored == original


# ── FlowStep ──────────────────────────────────────────────────


class TestFlowStep:
    """流程步骤模型。"""

    def test_required_fields_only(self):
        """仅提供必填字段可正常构造。"""
        step = FlowStep(step_id="s1", name="llm_call", node_type=NodeType.LLM)
        assert step.step_id == "s1"
        assert step.name == "llm_call"
        assert step.node_type is NodeType.LLM
        assert step.status == "running"
        assert step.parent_id is None
        assert step.children_ids == []
        assert step.input_data is None
        assert step.output_data is None
        assert step.llm_meta is None
        assert step.langsmith_run_id is None
        assert step.langsmith_run_url is None
        assert step.started_at == ""
        assert step.duration_ms == 0
        assert step.error is None

    def test_all_fields(self):
        """所有字段完整构造。"""
        llm = LLMMeta(model="glm-4.6v", total_tokens=100)
        step = FlowStep(
            step_id="s2",
            name="generate_script",
            node_type=NodeType.LLM,
            status="success",
            parent_id="s1",
            children_ids=["s3", "s4"],
            input_data={"prompt": "hello"},
            output_data={"text": "world"},
            llm_meta=llm,
            langsmith_run_id="run-abc123",
            langsmith_run_url="https://smith.langchain.com/runs/abc123",
            started_at="2026-04-02T10:00:00.000",
            duration_ms=1234.5,
            error=None,
        )
        assert step.step_id == "s2"
        assert step.name == "generate_script"
        assert step.node_type is NodeType.LLM
        assert step.status == "success"
        assert step.parent_id == "s1"
        assert step.children_ids == ["s3", "s4"]
        assert step.input_data == {"prompt": "hello"}
        assert step.output_data == {"text": "world"}
        assert step.llm_meta == llm
        assert step.langsmith_run_id == "run-abc123"
        assert step.langsmith_run_url == "https://smith.langchain.com/runs/abc123"
        assert step.started_at == "2026-04-02T10:00:00.000"
        assert step.duration_ms == 1234.5
        assert step.error is None

    def test_node_type_from_string(self):
        """node_type 字段接受字符串并自动转为枚举。"""
        step = FlowStep(step_id="s1", name="test", node_type="llm")
        assert step.node_type is NodeType.LLM

    def test_serialization_roundtrip(self):
        """序列化 → 反序列化保持一致。"""
        original = FlowStep(
            step_id="s1",
            name="test_step",
            node_type=NodeType.IMAGE_GEN,
            status="success",
            duration_ms=500.0,
            llm_meta=LLMMeta(model="qwen-v2"),
        )
        data = original.model_dump()
        restored = FlowStep.model_validate(data)
        assert restored == original

    def test_missing_required_field_raises(self):
        """缺少必填字段抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            FlowStep(step_id="s1")  # 缺少 name 和 node_type

    def test_children_ids_default_empty_list(self):
        """children_ids 默认为空列表。"""
        step = FlowStep(step_id="s1", name="test", node_type=NodeType.IO)
        assert step.children_ids == []

    def test_nested_llm_meta_serialization(self):
        """嵌套 LLMMeta 的序列化 → 反序列化保持一致。"""
        step = FlowStep(
            step_id="s1",
            name="call",
            node_type=NodeType.LLM,
            llm_meta=LLMMeta(model="glm", total_tokens=999),
        )
        json_str = step.model_dump_json()
        restored = FlowStep.model_validate_json(json_str)
        assert restored.llm_meta is not None
        assert restored.llm_meta.model == "glm"
        assert restored.llm_meta.total_tokens == 999


# ── FlowTrace ─────────────────────────────────────────────────


class TestFlowTrace:
    """流程追踪模型。"""

    def test_required_fields_only(self):
        """仅提供必填字段可正常构造。"""
        trace = FlowTrace(trace_id="t1", request_id="r1", flow_type="script")
        assert trace.trace_id == "t1"
        assert trace.request_id == "r1"
        assert trace.flow_type == "script"
        assert trace.status == "running"
        assert trace.created_at == ""
        assert trace.total_duration_ms == 0
        assert trace.steps == []
        assert trace.root_step_id is None
        assert trace.error is None

    def test_with_steps(self):
        """包含步骤的完整构造。"""
        step1 = FlowStep(step_id="s1", name="llm", node_type=NodeType.LLM)
        step2 = FlowStep(step_id="s2", name="image", node_type=NodeType.IMAGE_GEN)
        trace = FlowTrace(
            trace_id="t1",
            request_id="r1",
            flow_type="comic",
            status="success",
            total_duration_ms=3000.0,
            steps=[step1, step2],
            root_step_id="s1",
        )
        assert len(trace.steps) == 2
        assert trace.steps[0].name == "llm"
        assert trace.steps[1].name == "image"
        assert trace.root_step_id == "s1"
        assert trace.status == "success"

    def test_flow_type_accepts_any_string(self):
        """flow_type 不是 Literal，接受任意字符串。"""
        trace = FlowTrace(trace_id="t1", request_id="r1", flow_type="custom_flow")
        assert trace.flow_type == "custom_flow"

        trace2 = FlowTrace(trace_id="t2", request_id="r2", flow_type="anything_at_all")
        assert trace2.flow_type == "anything_at_all"

    def test_serialization_roundtrip(self):
        """序列化 → 反序列化保持一致。"""
        step = FlowStep(step_id="s1", name="step", node_type=NodeType.PROMPT)
        original = FlowTrace(
            trace_id="t1",
            request_id="r1",
            flow_type="script",
            steps=[step],
            root_step_id="s1",
        )
        data = original.model_dump()
        restored = FlowTrace.model_validate(data)
        assert restored == original
        assert len(restored.steps) == 1

    def test_json_roundtrip(self):
        """JSON 序列化 → 反序列化保持一致。"""
        original = FlowTrace(
            trace_id="t1",
            request_id="r1",
            flow_type="comic",
            status="failed",
            error="timeout",
        )
        json_str = original.model_dump_json()
        restored = FlowTrace.model_validate_json(json_str)
        assert restored == original
        assert restored.error == "timeout"

    def test_missing_required_field_raises(self):
        """缺少必填字段抛出 ValidationError。"""
        with pytest.raises(ValidationError):
            FlowTrace(trace_id="t1")  # 缺少 request_id 和 flow_type

    def test_steps_default_empty_list(self):
        """steps 默认为空列表。"""
        trace = FlowTrace(trace_id="t1", request_id="r1", flow_type="test")
        assert trace.steps == []
