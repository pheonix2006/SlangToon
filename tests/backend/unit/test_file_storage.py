"""FileStorage unit tests."""

import base64
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.storage.file_storage import FileStorage


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def storage(tmp_path):
    comic_dir = tmp_path / "comics"
    return FileStorage(str(comic_dir))


@pytest.fixture
def png_b64():
    """64x64 blue PNG base64."""
    img = Image.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# save_comic
# ---------------------------------------------------------------------------

class TestSaveComic:
    def test_saves_comic_png(self, storage, png_b64):
        result = storage.save_comic(png_b64, "test-uuid", "2026-01-01")

        comic_path = storage.comic_dir / "2026-01-01" / "test-uuid.png"
        assert comic_path.exists()

    def test_generates_thumbnail(self, storage, png_b64):
        result = storage.save_comic(png_b64, "test-uuid", "2026-01-01")

        thumb_path = storage.comic_dir / "2026-01-01" / "test-uuid_thumb.png"
        assert thumb_path.exists()
        thumb = Image.open(thumb_path)
        assert max(thumb.size) <= 256

    def test_returns_correct_urls(self, storage, png_b64):
        result = storage.save_comic(png_b64, "test-uuid", "2026-01-01")

        assert result["comic_url"] == "/data/comics/2026-01-01/test-uuid.png"
        assert result["thumbnail_url"] == "/data/comics/2026-01-01/test-uuid_thumb.png"

    def test_strips_data_prefix(self, storage, png_b64):
        data_uri = f"data:image/png;base64,{png_b64}"
        result = storage.save_comic(data_uri, "strip-uuid", "2026-03-29")

        comic_path = storage.comic_dir / "2026-03-29" / "strip-uuid.png"
        assert comic_path.exists()
        assert comic_path.stat().st_size > 0

    def test_creates_date_directory(self, storage, png_b64):
        storage.save_comic(png_b64, "dir-uuid", "2026-06-15")

        date_dir = storage.comic_dir / "2026-06-15"
        assert date_dir.is_dir()

    def test_comic_content_matches_input(self, storage, png_b64):
        result = storage.save_comic(png_b64, "content-uuid", "2026-01-01")

        comic_path = storage.comic_dir / "2026-01-01" / "content-uuid.png"
        saved_data = comic_path.read_bytes()
        assert saved_data == base64.b64decode(png_b64)


# ---------------------------------------------------------------------------
# _today_str
# ---------------------------------------------------------------------------

class TestTodayStr:
    def test_returns_string(self):
        result = FileStorage._today_str()
        assert isinstance(result, str)

    def test_format_yyyy_mm_dd(self):
        result = FileStorage._today_str()
        assert len(result) == 10
        parts = result.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # year
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 2  # day
