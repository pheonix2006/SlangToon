import base64
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import io


class FileStorage:
    """Local filesystem storage for comic images."""

    def __init__(self, comic_dir: str):
        self.comic_dir = Path(comic_dir)

    def _ensure_date_dir(self, date_str: str) -> Path:
        date_path = self.comic_dir / date_str
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    @staticmethod
    def _today_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def save_comic(self, image_base64: str, uuid_str: str, date_str: str) -> dict:
        """Save a comic image and generate thumbnail. Returns URL paths."""
        date_dir = self._ensure_date_dir(date_str)
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",", 1)[1]
        image_data = base64.b64decode(image_base64)

        img = Image.open(io.BytesIO(image_data))
        comic_name = f"{uuid_str}.png"
        comic_path = date_dir / comic_name
        img.save(comic_path, "PNG")

        thumb_name = f"{uuid_str}_thumb.png"
        thumb_path = date_dir / thumb_name
        thumb = img.copy()
        thumb.thumbnail((256, 256))
        thumb.save(thumb_path, "PNG")
        return {
            "comic_url": f"/data/comics/{date_str}/{comic_name}",
            "thumbnail_url": f"/data/comics/{date_str}/{thumb_name}",
        }
