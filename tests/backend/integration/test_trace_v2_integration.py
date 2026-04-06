"""Trace V2 端到端集成测试 — 验证完整链路: API请求 → trace记录 → traces查询。

使用 mock LLM 避免真实 API 调用，专注测试 trace 链路本身。
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

_backend_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))


def _clear_settings_cache():
    """Clear all settings-related lru_cache."""
    try:
        from app.dependencies import get_cached_settings
        get_cached_settings.cache_clear()
    except Exception:
        pass


def _setup_env(data_dir: Path, trace_enabled: bool = True):
    """Set environment variables for test."""
    os.environ["COMIC_STORAGE_DIR"] = str(data_dir / "comics")
    os.environ["HISTORY_FILE"] = str(data_dir / "history.json")
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = str(trace_enabled).lower()


def _cleanup_env():
    """Clean up environment variables."""
    for key in ["COMIC_STORAGE_DIR", "HISTORY_FILE", "TRACE_DIR", "TRACE_ENABLED"]:
        os.environ.pop(key, None)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_trace_env(tmp_path):
    """Set up temporary environment for trace testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "comics").mkdir()
    (data_dir / "traces").mkdir()
    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    _setup_env(data_dir, trace_enabled=True)
    _clear_settings_cache()
    yield data_dir
    _cleanup_env()
    _clear_settings_cache()


@pytest.fixture
def mock_llm_response():
    """Mock LLMResponse for script_node."""
    from app.services.llm_client import LLMResponse
    return LLMResponse(
        content=json.dumps({
            "slang": "Break a leg",
            "origin": "Western theater tradition",
            "explanation": "Used to wish good luck",
            "panel_count": 8,
            "panels": [
                {"scene": "A nervous actor paces.", "dialogue": "Narrator: \"Opening night...\""},
                {"scene": "Friends give thumbs up.", "dialogue": "Friend: \"You've got this!\""},
                {"scene": "Actor steps onto stage.", "dialogue": ""},
                {"scene": "Standing ovation!", "dialogue": "Narrator: \"Break a leg indeed.\""},
                {"scene": "Curtain closes.", "dialogue": ""},
                {"scene": "Cast celebrates.", "dialogue": "Director: \"Incredible!\""},
                {"scene": "Signed script.", "dialogue": ""},
                {"scene": "Actor under marquee.", "dialogue": "Narrator: \"And that's how you break a leg.\""},
            ],
        }),
        model="glm-4.6v",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
        finish_reason="stop",
    )


@pytest.fixture
def mock_image_b64():
    """Small valid PNG as base64."""
    from io import BytesIO
    from PIL import Image as PILImage
    import base64

    img = PILImage.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    raw = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{raw}"


@pytest_asyncio.fixture
async def app_client(tmp_trace_env):
    """ASGI test client."""
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _read_traces_from_dir(trace_dir: Path) -> list[dict]:
    """Read all traces from JSONL files."""
    traces = []
    for jsonl_file in trace_dir.glob("*.jsonl"):
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        traces.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return traces


# ── Tests: Script trace integration ────────────────────────────────────


class TestScriptTraceIntegration:
    """Script generation trace integration."""

    @pytest.mark.asyncio
    async def test_script_trace_saved_and_queryable(
        self, app_client, tmp_trace_env, mock_llm_response
    ):
        """Full chain: generate-script → trace saved → /api/traces queryable."""
        with patch(
            "app.services.llm_client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_llm_response,
        ):
            resp = await app_client.post("/api/generate-script", json={})

        # Verify API response
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0
        assert body["data"]["slang"] == "Break a leg"

        # Verify x-trace-id header
        trace_id = resp.headers.get("x-trace-id")
        assert trace_id is not None
        assert trace_id.startswith("t-")

        # Verify trace JSONL file
        traces = _read_traces_from_dir(tmp_trace_env / "traces")
        assert len(traces) >= 1

        trace_data = next(t for t in traces if t["trace_id"] == trace_id)
        assert trace_data["flow_type"] == "script"
        assert trace_data["status"] == "success"
        assert len(trace_data["nodes"]) >= 1

        # Verify script_node is recorded
        node_names = [n["name"] for n in trace_data["nodes"]]
        assert "script_node" in node_names

        # Query via /api/traces
        traces_resp = await app_client.get("/api/traces")
        assert traces_resp.status_code == 200
        traces_body = traces_resp.json()
        assert traces_body["code"] == 0
        assert len(traces_body["data"]["traces"]) >= 1

        # Query single trace
        detail_resp = await app_client.get(f"/api/traces/{trace_id}")
        assert detail_resp.status_code == 200
        detail_body = detail_resp.json()
        assert detail_body["code"] == 0
        assert detail_body["data"]["trace_id"] == trace_id

    @pytest.mark.asyncio
    async def test_trace_filters_by_flow_type(
        self, app_client, tmp_trace_env, mock_llm_response
    ):
        """Verify flow_type filtering."""
        with patch(
            "app.services.llm_client.LLMClient.chat",
            new_callable=AsyncMock,
            return_value=mock_llm_response,
        ):
            await app_client.post("/api/generate-script", json={})

        resp = await app_client.get("/api/traces?flow_type=script")
        body = resp.json()
        assert body["code"] == 0
        for trace in body["data"]["traces"]:
            assert trace["flow_type"] == "script"

        resp2 = await app_client.get("/api/traces?flow_type=comic")
        body2 = resp2.json()
        assert len(body2["data"]["traces"]) == 0

    @pytest.mark.asyncio
    async def test_trace_id_not_found(self, app_client, tmp_trace_env):
        """Query non-existent trace_id."""
        resp = await app_client.get("/api/traces/nonexistent-id")
        body = resp.json()
        assert body["code"] == 40001
        assert body["data"] is None


# ── Tests: Comic trace integration ─────────────────────────────────────


class TestComicTraceIntegration:
    """Comic generation trace integration."""

    @pytest.mark.asyncio
    async def test_comic_trace_saved(
        self, app_client, tmp_trace_env, mock_image_b64
    ):
        """ComicGraph trace is saved with all nodes."""
        script_data = {
            "slang": "Test",
            "origin": "Test",
            "explanation": "Test",
            "panel_count": 8,
            "panels": [
                {"scene": f"Scene {i}", "dialogue": ""} for i in range(8)
            ],
        }

        with patch(
            "app.services.image_gen_client.ImageGenClient.generate_from_text",
            new_callable=AsyncMock,
            return_value=mock_image_b64,
        ):
            resp = await app_client.post("/api/generate-comic", json=script_data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 0

        trace_id = resp.headers.get("x-trace-id")
        assert trace_id is not None

        # Verify trace
        traces = _read_traces_from_dir(tmp_trace_env / "traces")
        comic_trace = next(t for t in traces if t["trace_id"] == trace_id)
        assert comic_trace["flow_type"] == "comic"
        assert comic_trace["status"] == "success"

        node_names = [n["name"] for n in comic_trace["nodes"]]
        assert "prompt_node" in node_names
        assert "comic_node" in node_names
        assert "save_node" in node_names


# ── Tests: Error trace ─────────────────────────────────────────────────


class TestScriptTraceOnError:
    """Script generation failure trace."""

    @pytest.mark.asyncio
    async def test_llm_error_creates_failed_trace(
        self, app_client, tmp_trace_env
    ):
        """LLM failure records status=failed in trace."""
        from app.services.llm_client import LLMTimeoutError

        with patch(
            "app.services.llm_client.LLMClient.chat",
            new_callable=AsyncMock,
            side_effect=LLMTimeoutError("timeout"),
        ):
            resp = await app_client.post("/api/generate-script", json={})

        body = resp.json()
        assert body["code"] == 50001  # SCRIPT_LLM_FAILED

        trace_id = resp.headers.get("x-trace-id")
        assert trace_id is not None

        traces = _read_traces_from_dir(tmp_trace_env / "traces")
        assert len(traces) >= 1

        match = [t for t in traces if t["trace_id"] == trace_id]
        assert len(match) == 1
        assert match[0]["status"] == "failed"


# ── Tests: Trace disabled ──────────────────────────────────────────────


class TestTraceDisabled:
    """When trace_enabled=false, no traces are recorded."""

    @pytest.mark.asyncio
    async def test_no_trace_when_disabled(self, tmp_path):
        """trace disabled → no trace files."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "comics").mkdir()
        (data_dir / "traces").mkdir()
        (data_dir / "history.json").write_text("[]", encoding="utf-8")
        _setup_env(data_dir, trace_enabled=False)
        _clear_settings_cache()

        from app.services.llm_client import LLMResponse
        mock_resp = LLMResponse(
            content=json.dumps({
                "slang": "Test", "origin": "Test", "explanation": "Test",
                "panel_count": 8, "panels": [
                    {"scene": f"s{i}", "dialogue": ""} for i in range(8)
                ],
            }),
            model="test", prompt_tokens=10, completion_tokens=20, total_tokens=30,
            finish_reason="stop",
        )

        from app.main import create_app
        app = create_app()
        transport = ASGITransport(app=app)

        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            with patch(
                "app.services.llm_client.LLMClient.chat",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ):
                resp = await ac.post("/api/generate-script", json={})

        assert resp.status_code == 200
        assert "x-trace-id" not in resp.headers

        traces = _read_traces_from_dir(data_dir / "traces")
        assert len(traces) == 0

        _cleanup_env()
        _clear_settings_cache()
