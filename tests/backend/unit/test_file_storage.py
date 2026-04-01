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
    photo_dir = tmp_path / "photos"
    poster_dir = tmp_path / "posters"
    return FileStorage(str(photo_dir), str(poster_dir))


@pytest.fixture
def jpeg_b64():
    """100x100 red JPEG base64."""
    img = Image.new("RGB", (100, 100), "red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def png_b64():
    """64x64 blue PNG base64."""
    img = Image.new("RGB", (64, 64), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# save_photo
# ---------------------------------------------------------------------------

class TestSavePhoto:
    def test_saves_jpeg_file(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.suffix == ".jpg"
        assert file_path.stat().st_size > 0

    def test_saves_png_file(self, storage, png_b64):
        result = storage.save_photo(png_b64, "png")

        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.suffix == ".png"

    def test_saves_webp_file(self, storage):
        img = Image.new("RGB", (50, 50), "green")
        buf = BytesIO()
        img.save(buf, format="WEBP")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        result = storage.save_photo(b64, "webp")
        file_path = Path(result["file_path"])
        assert file_path.suffix == ".webp"

    def test_returns_correct_url(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        assert result["url"].startswith("/data/photos/")
        assert result["url"].endswith(".jpg")

    def test_returns_uuid(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        assert "uuid" in result
        assert len(result["uuid"]) == 32  # hex uuid

    def test_returns_date_string(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        assert "date" in result
        # date format YYYY-MM-DD
        assert len(result["date"]) == 10

    def test_creates_date_directory(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        date_dir = storage.photo_dir / result["date"]
        assert date_dir.is_dir()

    def test_jpeg_format_uses_jpg_extension(self, storage, jpeg_b64):
        result = storage.save_photo(jpeg_b64, "jpeg")

        assert result["file_path"].endswith(".jpg")

    def test_each_save_gets_unique_uuid(self, storage, jpeg_b64):
        r1 = storage.save_photo(jpeg_b64, "jpeg")
        r2 = storage.save_photo(jpeg_b64, "jpeg")

        assert r1["uuid"] != r2["uuid"]


# ---------------------------------------------------------------------------
# save_poster
# ---------------------------------------------------------------------------

class TestSavePoster:
    def test_saves_poster_png(self, storage, png_b64):
        result = storage.save_poster(png_b64, "test-uuid", "2026-01-01")

        poster_path = storage.poster_dir / "2026-01-01" / "test-uuid.png"
        assert poster_path.exists()

    def test_generates_thumbnail(self, storage, png_b64):
        result = storage.save_poster(png_b64, "test-uuid", "2026-01-01")

        thumb_path = storage.poster_dir / "2026-01-01" / "test-uuid_thumb.png"
        assert thumb_path.exists()
        thumb = Image.open(thumb_path)
        assert max(thumb.size) <= 256

    def test_returns_correct_urls(self, storage, png_b64):
        result = storage.save_poster(png_b64, "test-uuid", "2026-01-01")

        assert result["poster_url"] == "/data/posters/2026-01-01/test-uuid.png"
        assert result["thumbnail_url"] == "/data/posters/2026-01-01/test-uuid_thumb.png"

    def test_strips_data_prefix(self, storage, png_b64):
        data_uri = f"data:image/png;base64,{png_b64}"
        result = storage.save_poster(data_uri, "strip-uuid", "2026-03-29")

        poster_path = storage.poster_dir / "2026-03-29" / "strip-uuid.png"
        assert poster_path.exists()
        assert poster_path.stat().st_size > 0

    def test_creates_date_directory_poster(self, storage, png_b64):
        storage.save_poster(png_b64, "dir-uuid", "2026-06-15")

        date_dir = storage.poster_dir / "2026-06-15"
        assert date_dir.is_dir()

    def test_poster_content_matches_input(self, storage, png_b64):
        result = storage.save_poster(png_b64, "content-uuid", "2026-01-01")

        poster_path = storage.poster_dir / "2026-01-01" / "content-uuid.png"
        saved_data = poster_path.read_bytes()
        assert saved_data == base64.b64decode(png_b64)
