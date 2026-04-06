"""Tests for trace_collector -- graph execution + local trace storage."""

import json
import pytest

from app.graphs.script_graph import build_script_graph
from app.graphs.trace_collector import invoke_with_trace
from app.graphs.trace_store import TraceStore
from app.services.llm_client import LLMResponse


@pytest.mark.asyncio
async def test_invoke_with_trace_saves_local_trace(tmp_data_dir):
    """invoke_with_trace executes graph and saves local trace."""
    from app.config import Settings
    settings = Settings()

    mock_data = {
        "slang": "Test",
        "origin": "Test origin",
        "explanation": "Test explanation",
        "panel_count": 8,
        "panels": [{"scene": f"S{i}", "dialogue": ""} for i in range(8)],
    }

    import unittest.mock as mock
    with mock.patch("app.nodes.script_node.LLMClient") as MockClient:
        instance = MockClient.return_value
        instance.chat = mock.AsyncMock(
            return_value=LLMResponse(content=json.dumps(mock_data), model="glm-4.6v")
        )
        MockClient.extract_json_from_content = staticmethod(
            lambda c: json.loads(c) if isinstance(c, str) else c
        )

        graph = build_script_graph()
        result, trace_id = await invoke_with_trace(
            graph, {"trigger": "ok"}, settings, flow_type="script",
        )

    assert result["slang"] == "Test"
    assert trace_id.startswith("t-")

    # Verify local trace saved
    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
    found = store.get_by_trace_id(trace_id)
    assert found is not None
    assert found.flow_type == "script"
    assert found.status == "success"
    assert len(found.nodes) >= 1
