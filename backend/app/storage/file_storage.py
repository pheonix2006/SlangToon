import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import io


class FileStorage:
    """本地文件系统存储"""

    def __init__(self, photo_dir: str, poster_dir: str):
        self.photo_dir = Path(photo_dir)
        self.poster_dir = Path(poster_dir)

    def _ensure_date_dir(self, base_dir: Path, date_str: str) -> Path:
        date_path = base_dir / date_str
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    def _today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def save_photo(self, image_base64: str, image_format: str) -> dict:
        file_uuid = uuid.uuid4().hex
        date_str = self._today_str()
        ext = "jpg" if image_format == "jpeg" else image_format
        date_dir = self._ensure_date_dir(self.photo_dir, date_str)
        file_name = f"{file_uuid}.{ext}"
        file_path = date_dir / file_name
        image_data = base64.b64decode(image_base64)
        file_path.write_bytes(image_data)
        return {
            "file_path": str(file_path),
            "url": f"/data/photos/{date_str}/{file_name}",
            "uuid": file_uuid,
            "date": date_str,
        }

    def save_poster(self, image_base64: str, uuid_str: str, date_str: str) -> dict:
        date_dir = self._ensure_date_dir(self.poster_dir, date_str)
        # 剥离可能的 data:image/...;base64, 前缀
        if image_base64.startswith("data:image"):
            image_base64 = image_base64.split(",", 1)[1]
        image_data = base64.b64decode(image_base64)

        # 用 PIL 确保保存为真正的 PNG 格式，避免扩展名与实际格式不匹配
        img = Image.open(io.BytesIO(image_data))
        poster_name = f"{uuid_str}.png"
        poster_path = date_dir / poster_name
        img.save(poster_path, "PNG")

        # 生成缩略图
        thumb_name = f"{uuid_str}_thumb.png"
        thumb_path = date_dir / thumb_name
        thumb = img.copy()
        thumb.thumbnail((256, 256))
        thumb.save(thumb_path, "PNG")
        return {
            "poster_url": f"/data/posters/{date_str}/{poster_name}",
            "thumbnail_url": f"/data/posters/{date_str}/{thumb_name}",
        }
