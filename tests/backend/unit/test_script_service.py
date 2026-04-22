"""script_service 共享逻辑单元测试。"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.services.script_service import build_script_context, validate_and_finalize


class TestBuildScriptContext:
    def test_returns_prompt_and_blacklist(self, tmp_data_dir):
        from app.config import Settings
        settings = Settings()
        system_prompt, blacklist = build_script_context(settings)
        assert isinstance(system_prompt, str)
        assert "comic scriptwriter" in system_prompt

    def test_blacklist_items_in_prompt(self, tmp_data_dir):
        from app.config import Settings
        settings = Settings()
        mock_bl = MagicMock()
        mock_bl.get_recent.return_value = ["Old Slang A", "Old Slang B"]
        with patch("app.services.script_service.SlangBlacklist", return_value=mock_bl):
            prompt, _ = build_script_context(settings)
        assert "Old Slang A" in prompt
        assert "DO NOT pick" in prompt


class TestValidateAndFinalize:
    def test_valid_4_panels(self, tmp_data_dir):
        content = json.dumps({
            "slang": "Test", "origin": "T", "explanation": "T",
            "panel_count": 4,
            "panels": [{"scene": f"S{i}", "dialogue": ""} for i in range(4)],
        })
        mock_bl = MagicMock()
        result = validate_and_finalize(content, mock_bl)
        assert result["slang"] == "Test"
        assert result["panel_count"] == 4
        mock_bl.add.assert_called_once_with("Test")

    def test_invalid_panel_count_raises(self, tmp_data_dir):
        content = json.dumps({
            "slang": "Bad", "origin": "T", "explanation": "T",
            "panel_count": 2, "panels": [{"scene": "A", "dialogue": ""}],
        })
        mock_bl = MagicMock()
        with pytest.raises(ValueError, match="Invalid panel_count"):
            validate_and_finalize(content, mock_bl)
        mock_bl.add.assert_not_called()

    def test_panel_count_mismatch_raises(self, tmp_data_dir):
        content = json.dumps({
            "slang": "Bad", "origin": "T", "explanation": "T",
            "panel_count": 4, "panels": [{"scene": "A", "dialogue": ""}],
        })
        mock_bl = MagicMock()
        with pytest.raises(ValueError, match="panels length"):
            validate_and_finalize(content, mock_bl)
        mock_bl.add.assert_not_called()
