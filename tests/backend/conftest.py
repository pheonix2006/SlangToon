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
    (data_dir / "photos").mkdir()
    (data_dir / "posters").mkdir()
    (data_dir / "history.json").write_text("[]", encoding="utf-8")
    os.environ["PHOTO_STORAGE_DIR"] = str(data_dir / "photos")
    os.environ["POSTER_STORAGE_DIR"] = str(data_dir / "posters")
    os.environ["HISTORY_FILE"] = str(data_dir / "history.json")
    (data_dir / "traces").mkdir()
    os.environ["TRACE_DIR"] = str(data_dir / "traces")
    os.environ["TRACE_ENABLED"] = "true"
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
def sample_image_base64() -> str:
    img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def mock_llm_options():
    return [
        {"name": "主题A", "brief": "描述A"},
        {"name": "主题B", "brief": "描述B"},
        {"name": "主题C", "brief": "描述C"},
        {"name": "主题D", "brief": "描述D"},
        {"name": "主题E", "brief": "描述E"},
    ]


@pytest.fixture
def mock_llm_response_text(mock_llm_options):
    return json.dumps({"options": mock_llm_options})


@pytest.fixture
def mock_compose_response():
    return json.dumps({"prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, full body portrait of a person standing heroically in a cyberpunk city street at night, neon signs reflecting on wet pavement, cinematic wide shot, volumetric lighting, deep sapphire blue and iridescent cyan color palette, leather jacket and glowing accessories, rain particles, 85mm lens, shallow depth of field"})


@pytest.fixture
def mock_image_gen_b64():
    img = Image.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def trace_store(tmp_data_dir):
    """创建临时 TraceStore 实例。"""
    from app.flow_log.trace_store import TraceStore
    return TraceStore(str(tmp_data_dir / "traces"), retention_days=7)
