import pytest
import json
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
    async def test_prompt_within_max_length(self, mock_script_data):
        """The built prompt should not exceed MAX_PROMPT_LENGTH characters."""
        from app.prompts.comic_prompt import build_comic_prompt, MAX_PROMPT_LENGTH
        prompt = build_comic_prompt(
            slang=mock_script_data["slang"],
            origin=mock_script_data["origin"],
            explanation=mock_script_data["explanation"],
            panels=mock_script_data["panels"],
        )
        assert len(prompt) <= MAX_PROMPT_LENGTH

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


class TestTokenCondenseRetry:
    """Tests for token-based prompt condensing and retry logic."""

    @pytest.mark.asyncio
    async def test_normal_flow_no_condense_needed(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """When prompt is within token limit, no condense should occur."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client), \
             patch("app.services.comic_service.count_tokens", return_value=100):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert "history_id" in result
        mock_img_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_condense_called_when_over_token_limit(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """When prompt exceeds token limit, LLM condense should be called."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        # First count_tokens returns 1200 (over limit), second returns 500 (after condense)
        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client), \
             patch("app.services.comic_service.count_tokens", side_effect=[1200, 500]), \
             patch("app.services.comic_service._condense_via_llm", new_callable=AsyncMock, return_value="shortened prompt"):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert "history_id" in result

    @pytest.mark.asyncio
    async def test_llm_condense_fails_fallback_to_truncation(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """When LLM condense fails, fallback to token truncation should succeed."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        # count_tokens returns over limit once; condense returns None (failed),
        # so token_count stays 1200, triggering force truncation
        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client), \
             patch("app.services.comic_service.count_tokens", return_value=1200), \
             patch("app.services.comic_service._condense_via_llm", new_callable=AsyncMock, return_value=None), \
             patch("app.services.comic_service._truncate_prompt_to_tokens", return_value="truncated prompt"):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert "history_id" in result
        mock_img_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_still_over_limit_after_condense_force_truncation(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """When still over limit after condense, force truncation should be applied."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        # count_tokens: 1200 (initial) -> 1050 (after condense, still over limit)
        # This triggers force truncation since 1050 > 950
        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client), \
             patch("app.services.comic_service.count_tokens", side_effect=[1200, 1050]), \
             patch("app.services.comic_service._condense_via_llm", new_callable=AsyncMock, return_value="still long prompt"), \
             patch("app.services.comic_service._truncate_prompt_to_tokens", return_value="force truncated"):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert "history_id" in result
        mock_img_client.generate_from_text.assert_called_once()
