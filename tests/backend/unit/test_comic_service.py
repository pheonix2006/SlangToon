import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.image_gen_client import ImageGenClient, ImageGenApiError
from app.services.comic_service import generate_comic


def _make_settings(**overrides):
    from app.config import Settings
    defaults = dict(
        OPENAI_API_KEY="test-key",
        OPENAI_BASE_URL="https://api.example.com/v4",
        OPENAI_MODEL="test-model",
        vision_llm_max_tokens=4096,
        vision_llm_timeout=5,
        vision_llm_max_retries=2,
        qwen_image_apikey="test-img-key",
        qwen_image_base_url="https://dashscope.example.com/api/v1",
        qwen_image_model="qwen-image-2.0",
        qwen_image_timeout=5,
        qwen_image_max_retries=2,
        comic_storage_dir="/tmp/test-comics",
        history_file="/tmp/test-history.json",
        max_history_records=100,
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


class TestGenerateComic:
    @pytest.mark.asyncio
    async def test_valid_generation_returns_comic_data(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """generate_comic should return comic_url, thumbnail_url, history_id."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert "thumbnail_url" in result
        assert "history_id" in result
        assert result["history_id"]  # non-empty string
        mock_img_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_prompt_within_800_chars(self, mock_script_data):
        """The built prompt should not exceed 800 characters."""
        from app.prompts.comic_prompt import build_comic_prompt
        prompt = build_comic_prompt(
            slang=mock_script_data["slang"],
            origin=mock_script_data["origin"],
            explanation=mock_script_data["explanation"],
            panels=mock_script_data["panels"],
        )
        assert len(prompt) <= 800

    @pytest.mark.asyncio
    async def test_image_gen_error_propagates(self, mock_script_data, tmp_data_dir):
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(
            side_effect=ImageGenApiError("API error")
        )

        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
            with pytest.raises(ImageGenApiError):
                await generate_comic(mock_script_data, settings)

    @pytest.mark.asyncio
    async def test_comic_saved_to_disk(self, mock_script_data, mock_image_gen_b64, tmp_data_dir):
        """Verify comic image is actually saved to disk."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
            result = await generate_comic(mock_script_data, settings)

        # Verify file exists on disk
        from pathlib import Path
        # URL is /data/comics/{date}/{name}, actual storage is at comic_storage_dir/{date}/{name}
        comic_filename = Path(result["comic_url"]).name
        thumb_filename = Path(result["thumbnail_url"]).name
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        comic_dir = Path(settings.comic_storage_dir) / date_str
        assert (comic_dir / comic_filename).exists()
        assert (comic_dir / thumb_filename).exists()
