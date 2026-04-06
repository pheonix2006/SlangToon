"""Tests for ScriptGraph -- end-to-end LangGraph script generation."""

import json
import pytest

from app.graphs.script_graph import build_script_graph
from app.services.llm_client import LLMResponse


@pytest.mark.asyncio
async def test_script_graph_produces_valid_output(tmp_data_dir):
    """ScriptGraph end-to-end: mock LLM -> verify final state contains script data."""
    from app.config import Settings
    settings = Settings()

    mock_data = {
        "slang": "Break a leg",
        "origin": "Western theater",
        "explanation": "Good luck wish",
        "panel_count": 8,
        "panels": [{"scene": f"Scene {i}", "dialogue": ""} for i in range(8)],
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
        result = await graph.ainvoke(
            {"trigger": "ok_gesture"},
            config={"configurable": {"settings": settings}},
        )

    assert result["slang"] == "Break a leg"
    assert result["panel_count"] == 8
    assert len(result["panels"]) == 8
