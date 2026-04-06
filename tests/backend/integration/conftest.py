import sys
from pathlib import Path

# Ensure backend/ is on sys.path so `from app.*` imports work
_backend_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

import os

import pytest

from app.config import Settings


def _has_api_keys() -> bool:
    """Check if required API keys are configured in .env."""
    try:
        s = Settings()
        return bool(s.openai_api_key and s.qwen_image_apikey)
    except Exception:
        return False


@pytest.fixture
def real_settings(tmp_path) -> Settings:
    """Load real Settings from .env with temp storage paths."""
    os.environ["COMIC_STORAGE_DIR"] = str(tmp_path / "comics")
    os.environ["HISTORY_FILE"] = str(tmp_path / "history.json")
    os.environ["TRACE_DIR"] = str(tmp_path / "traces")
    os.environ["TRACE_ENABLED"] = "false"
    (tmp_path / "comics").mkdir(exist_ok=True)
    (tmp_path / "traces").mkdir(exist_ok=True)
    (tmp_path / "history.json").write_text("[]", encoding="utf-8")
    return Settings()


@pytest.fixture
def skip_without_api_keys():
    """Skip test if API keys are not configured."""
    if not _has_api_keys():
        pytest.skip("API keys not configured in .env — skipping integration test")
