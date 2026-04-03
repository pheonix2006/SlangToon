import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm_client import LLMClient, LLMResponse, LLMTimeoutError, LLMApiError
from app.services.script_service import generate_script


def _make_settings(**overrides):
    from app.config import Settings
    defaults = dict(
        OPENAI_API_KEY="test-key",
        OPENAI_BASE_URL="https://api.example.com/v4",
        OPENAI_MODEL="test-model",
        vision_llm_max_tokens=4096,
        vision_llm_timeout=5,
        vision_llm_max_retries=2,
    )
    defaults.update(overrides)
    return Settings.model_validate(defaults)


class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_valid_response_returns_script_data(self, mock_script_data):
        settings = _make_settings()

        with patch.object(LLMClient, "__init__", return_value=None), \
             patch.object(LLMClient, "chat", new_callable=AsyncMock, return_value=LLMResponse(content=json.dumps(mock_script_data), model="test-model")) as mock_chat:
            result = await generate_script(settings)

        assert result["slang"] == "Break a leg"
        assert result["panel_count"] == 4
        assert len(result["panels"]) == 4
        mock_chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_timeout_raises_script_error(self):
        settings = _make_settings()

        with patch.object(LLMClient, "__init__", return_value=None), \
             patch.object(LLMClient, "chat", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            with pytest.raises(LLMTimeoutError):
                await generate_script(settings)

    @pytest.mark.asyncio
    async def test_llm_api_error_propagates(self):
        settings = _make_settings()

        with patch.object(LLMClient, "__init__", return_value=None), \
             patch.object(LLMClient, "chat", new_callable=AsyncMock, side_effect=LLMApiError("4xx error")):
            with pytest.raises(LLMApiError):
                await generate_script(settings)

    @pytest.mark.asyncio
    async def test_invalid_panel_count_raises(self, mock_script_data):
        """panel_count outside 4-6 range should raise ValueError."""
        settings = _make_settings()
        bad_data = {**mock_script_data, "panel_count": 3}

        with patch.object(LLMClient, "__init__", return_value=None), \
             patch.object(LLMClient, "chat", new_callable=AsyncMock, return_value=LLMResponse(content=json.dumps(bad_data), model="test-model")):
            with pytest.raises(ValueError, match="panel_count"):
                await generate_script(settings)

    @pytest.mark.asyncio
    async def test_panels_length_mismatch_raises(self, mock_script_data):
        """panels length != panel_count should raise ValueError."""
        settings = _make_settings()
        bad_data = {**mock_script_data, "panel_count": 4, "panels": mock_script_data["panels"][:3]}

        with patch.object(LLMClient, "__init__", return_value=None), \
             patch.object(LLMClient, "chat", new_callable=AsyncMock, return_value=LLMResponse(content=json.dumps(bad_data), model="test-model")):
            with pytest.raises(ValueError, match="panels length"):
                await generate_script(settings)
