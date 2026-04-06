"""Integration tests — real GLM-4.6V and Qwen Image 2.0 API calls via LangGraph.

These tests hit REAL external APIs and require valid API keys in .env.

Run only integration tests:
    uv run pytest tests/backend/integration/test_real_api.py -v -s

Skip integration tests (unit only):
    uv run pytest tests/backend/unit/ -v

Run all:
    uv run pytest tests/backend/ -v
"""

import asyncio
import base64
import os
import sys
from io import BytesIO
from pathlib import Path

import pytest
import pytest_asyncio
from PIL import Image

# Ensure backend/ is on sys.path
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from app.config import Settings


def _has_api_keys() -> bool:
    """Check if required API keys are configured in .env."""
    try:
        s = Settings()
        return bool(s.openai_api_key and s.qwen_image_apikey)
    except Exception:
        return False


skip_no_keys = pytest.mark.skipif(
    not _has_api_keys(),
    reason="API keys not configured in .env",
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def real_settings(tmp_path) -> Settings:
    """Load real Settings from .env with temp storage paths."""
    os.environ["COMIC_STORAGE_DIR"] = str(tmp_path / "comics")
    os.environ["HISTORY_FILE"] = str(tmp_path / "history.json")
    os.environ["TRACE_DIR"] = str(tmp_path / "traces")
    os.environ["TRACE_ENABLED"] = "true"
    (tmp_path / "comics").mkdir(exist_ok=True)
    (tmp_path / "traces").mkdir(exist_ok=True)
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    # Clear cached settings
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()
    yield Settings()
    get_cached_settings.cache_clear()


# ── Stage 1: ScriptGraph — real GLM-4.6V call ──────────────────────────


@skip_no_keys
@pytest.mark.asyncio
class TestScriptGraph:
    """ScriptGraph: real GLM-4.6V call via LangGraph."""

    async def test_script_graph_returns_valid_data(self, real_settings):
        """ScriptGraph returns slang + 8-12 panel comic script."""
        from app.graphs.script_graph import build_script_graph

        graph = build_script_graph()
        result = await graph.ainvoke(
            {"trigger": "ok_gesture"},
            config={"configurable": {"settings": real_settings}},
        )

        # Verify all required fields
        assert result["slang"], "slang is empty"
        assert result["origin"], "origin is empty"
        assert result["explanation"], "explanation is empty"
        assert 8 <= result["panel_count"] <= 12, f"panel_count={result['panel_count']}"
        assert len(result["panels"]) == result["panel_count"]

        for i, panel in enumerate(result["panels"]):
            assert "scene" in panel, f"Panel {i} missing 'scene'"
            assert panel["scene"], f"Panel {i} has empty 'scene'"

    async def test_script_graph_with_trace_collector(self, real_settings):
        """invoke_with_trace records local trace for script flow."""
        from app.graphs.script_graph import build_script_graph
        from app.graphs.trace_collector import invoke_with_trace
        from app.graphs.trace_store import TraceStore

        graph = build_script_graph()
        result, trace_id = await invoke_with_trace(
            graph,
            {"trigger": "ok_gesture"},
            real_settings,
            flow_type="script",
        )

        assert result["slang"]
        assert trace_id.startswith("t-")

        # Verify local trace
        store = TraceStore(real_settings.trace_dir, real_settings.trace_retention_days)
        trace = store.get_by_trace_id(trace_id)
        assert trace is not None
        assert trace.flow_type == "script"
        assert trace.status == "success"
        assert any(n.name == "script_node" for n in trace.nodes)


# ── Stage 2: ComicGraph — real Qwen Image 2.0 call ────────────────────


@skip_no_keys
@pytest.mark.asyncio
class TestComicGraph:
    """ComicGraph: real Qwen Image 2.0 call via LangGraph."""

    async def test_comic_graph_full_pipeline(self, real_settings):
        """ComicGraph: prompt_node -> comic_node -> save_node with real APIs."""
        from app.graphs.comic_graph import build_comic_graph

        graph = build_comic_graph()
        inputs = {
            "slang": "Break a leg",
            "origin": "Western theater",
            "explanation": "Wish good luck before a performance",
            "panel_count": 8,
            "panels": [
                {
                    "scene": f"A simple manga panel scene {i+1} with a character",
                    "dialogue": f"Dialogue {i+1}" if i % 2 == 0 else "",
                }
                for i in range(8)
            ],
        }

        result = await graph.ainvoke(
            inputs,
            config={"configurable": {"settings": real_settings}},
        )

        assert result["comic_url"].startswith("/data/comics/")
        assert result["thumbnail_url"].startswith("/data/comics/")
        assert result["history_id"]

    async def test_comic_image_is_valid(self, real_settings):
        """Generated comic image can be decoded and opened as an image."""
        from app.graphs.comic_graph import build_comic_graph

        graph = build_comic_graph()
        inputs = {
            "slang": "Test Comic",
            "origin": "Test",
            "explanation": "Test image generation",
            "panel_count": 8,
            "panels": [
                {"scene": f"A blue square with number {i+1}", "dialogue": ""}
                for i in range(8)
            ],
        }

        result = await graph.ainvoke(
            inputs,
            config={"configurable": {"settings": real_settings}},
        )

        # Read saved file and verify it's a valid image
        from pathlib import Path as P
        comic_path = P(real_settings.comic_storage_dir) / result["comic_url"].replace("/data/comics/", "")
        assert comic_path.exists(), f"Comic file not found: {comic_path}"

        img = Image.open(comic_path)
        assert img.size[0] > 0 and img.size[1] > 0

    async def test_comic_graph_state_propagation(self, real_settings):
        """Verify State propagates correctly between nodes via astream."""
        from app.graphs.comic_graph import build_comic_graph

        graph = build_comic_graph()
        inputs = {
            "slang": "State Test",
            "origin": "Test",
            "explanation": "Testing state propagation",
            "panel_count": 8,
            "panels": [
                {"scene": f"Scene {i+1}", "dialogue": ""}
                for i in range(8)
            ],
        }

        node_outputs = {}
        async for chunk in graph.astream(
            inputs,
            config={"configurable": {"settings": real_settings}},
            stream_mode="updates",
        ):
            for node_name, output in chunk.items():
                node_outputs[node_name] = output

        # Verify execution chain
        assert "prompt_node" in node_outputs
        assert "comic_prompt" in node_outputs["prompt_node"]

        assert "comic_node" in node_outputs
        assert "image_base64" in node_outputs["comic_node"]

        assert "save_node" in node_outputs
        assert "comic_url" in node_outputs["save_node"]


# ── Stage 3: Full E2E Flow — script -> comic ───────────────────────────


@skip_no_keys
@pytest.mark.asyncio
class TestFullE2EFlow:
    """Full pipeline: ScriptGraph -> ComicGraph with real API calls."""

    async def test_script_then_comic(self, real_settings):
        """Generate script with GLM-4.6V, then generate comic with Qwen."""
        from app.graphs.script_graph import build_script_graph
        from app.graphs.comic_graph import build_comic_graph

        # Step 1: Generate script
        script_graph = build_script_graph()
        script_result = await script_graph.ainvoke(
            {"trigger": "ok_gesture"},
            config={"configurable": {"settings": real_settings}},
        )
        assert script_result["slang"]
        assert len(script_result["panels"]) == script_result["panel_count"]

        # Step 2: Generate comic from script
        comic_graph = build_comic_graph()
        comic_result = await comic_graph.ainvoke(
            script_result,
            config={"configurable": {"settings": real_settings}},
        )
        assert comic_result["comic_url"].startswith("/data/comics/")
        assert comic_result["history_id"]

    async def test_history_recorded(self, real_settings):
        """After full flow, a history record exists."""
        from app.graphs.script_graph import build_script_graph
        from app.graphs.comic_graph import build_comic_graph
        from app.services.history_service import HistoryService

        # Full flow
        script_graph = build_script_graph()
        script_result = await script_graph.ainvoke(
            {"trigger": "ok_gesture"},
            config={"configurable": {"settings": real_settings}},
        )

        comic_graph = build_comic_graph()
        comic_result = await comic_graph.ainvoke(
            script_result,
            config={"configurable": {"settings": real_settings}},
        )

        # Verify history
        history = HistoryService(real_settings.history_file, real_settings.max_history_records)
        page = history.get_page(page=1, page_size=10)
        assert page["total"] >= 1
        assert any(item["id"] == comic_result["history_id"] for item in page["items"])

    async def test_trace_collector_full_flow(self, real_settings):
        """Full flow with trace_collector produces both local and state traces."""
        from app.graphs.script_graph import build_script_graph
        from app.graphs.comic_graph import build_comic_graph
        from app.graphs.trace_collector import invoke_with_trace
        from app.graphs.trace_store import TraceStore

        # Script with trace
        script_graph = build_script_graph()
        script_result, script_trace_id = await invoke_with_trace(
            script_graph,
            {"trigger": "ok_gesture"},
            real_settings,
            flow_type="script",
        )

        # Comic with trace
        comic_graph = build_comic_graph()
        comic_result, comic_trace_id = await invoke_with_trace(
            comic_graph,
            script_result,
            real_settings,
            flow_type="comic",
        )

        # Verify local traces
        store = TraceStore(real_settings.trace_dir, real_settings.trace_retention_days)

        script_trace = store.get_by_trace_id(script_trace_id)
        assert script_trace is not None
        assert script_trace.flow_type == "script"
        assert script_trace.status == "success"

        comic_trace = store.get_by_trace_id(comic_trace_id)
        assert comic_trace is not None
        assert comic_trace.flow_type == "comic"
        assert comic_trace.status == "success"
        assert any(n.name == "prompt_node" for n in comic_trace.nodes)
        assert any(n.name == "comic_node" for n in comic_trace.nodes)
        assert any(n.name == "save_node" for n in comic_trace.nodes)
