import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `from app.*` imports work
_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

import json
import os
import pytest
import pytest_asyncio
import base64
from io import BytesIO
from PIL import Image
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def tmp_data_dir(tmp_path):
    """创建临时 data 目录结构并设置环境变量。"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "comics").mkdir()
    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    os.environ["COMIC_STORAGE_DIR"] = str(data_dir / "comics")
    os.environ["HISTORY_FILE"] = str(data_dir / "history.json")
    (data_dir / "traces").mkdir()
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = "true"
    # Clear cached settings so new env vars take effect
    from app.dependencies import get_cached_settings
    get_cached_settings.cache_clear()
    yield data_dir


@pytest_asyncio.fixture
async def client(tmp_data_dir):
    """FastAPI TestClient — 使用真实 ASGI app。"""
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_script_data():
    """Mock slang + comic script response from LLM."""
    return {
        "slang": "Break a leg",
        "origin": "Western theater tradition",
        "explanation": "Used to wish good luck before a performance",
        "panel_count": 4,
        "panels": [
            {
                "scene": "A nervous actor paces backstage, clutching a crumpled script. The stage manager glances at the clock.",
                "dialogue": "Narrator: 'It was opening night...'",
            },
            {
                "scene": "Friends gather around the actor, giving thumbs up with warm smiles.",
                "dialogue": "Friend: 'You got this!'",
            },
            {
                "scene": "The actor steps onto the stage under a bright spotlight. The audience is a sea of silhouettes.",
                "dialogue": "",
            },
            {
                "scene": "Standing ovation! Confetti falls. The actor beams with joy and happy tears.",
                "dialogue": "Narrator: 'Break a leg indeed.'",
            },
        ],
    }


@pytest.fixture
def mock_script_response_text(mock_script_data):
    """Mock LLM JSON response text for script generation."""
    return json.dumps(mock_script_data)


@pytest.fixture
def mock_comic_prompt():
    """Mock visual prompt for comic generation."""
    return "A 4-panel 2x2 grid comic strip, 16:9 landscape. Panel 1: A nervous actor paces backstage. Panel 2: Friends give thumbs up. Panel 3: Actor steps onto spotlight stage. Panel 4: Standing ovation. Speech bubbles with dialogue. Clean line art, warm color palette."


@pytest.fixture
def mock_image_gen_b64():
    img = Image.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def trace_store(tmp_data_dir):
    """创建临时 TraceStore 实例。"""
    from app.graphs.trace_store import TraceStore
    return TraceStore(str(tmp_data_dir / "traces"), retention_days=7)
