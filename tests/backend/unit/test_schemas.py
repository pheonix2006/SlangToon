import pytest
from pydantic import ValidationError

from app.schemas.script import ScriptData, ScriptRequest, Panel, ScriptResponse
from app.schemas.comic import ComicRequest, ComicResponse
from app.schemas.history import HistoryItem


class TestScriptData:
    def test_valid_script_data(self):
        data = ScriptData(
            slang="Break a leg",
            origin="Western theater tradition",
            explanation="Used to wish good luck",
            panel_count=4,
            panels=[Panel(scene="A scene", dialogue="")] * 4,
        )
        assert data.slang == "Break a leg"
        assert len(data.panels) == 4

    def test_rejects_panel_count_below_3(self):
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=2,
                panels=[Panel(scene="x")] * 2,
            )

    def test_rejects_panel_count_above_6(self):
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=7,
                panels=[Panel(scene="x")] * 7,
            )

    def test_panel_count_mismatch_with_list_length(self):
        with pytest.raises(ValidationError):
            ScriptData(
                slang="test", origin="test", explanation="test",
                panel_count=4,
                panels=[Panel(scene="x")] * 3,
            )


class TestScriptRequest:
    def test_empty_request(self):
        req = ScriptRequest()
        assert True

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            ScriptRequest(bogus="value")


class TestComicRequest:
    def test_valid_request(self):
        panels = [Panel(scene="test", dialogue="")] * 4
        req = ComicRequest(
            slang="Break a leg", origin="Western", explanation="Good luck",
            panel_count=4, panels=panels,
        )
        assert req.slang == "Break a leg"

    def test_missing_panels_raises(self):
        with pytest.raises(ValidationError):
            ComicRequest(slang="test", origin="test", explanation="test", panel_count=4, panels=[])


class TestHistoryItem:
    def test_valid_item(self):
        item = HistoryItem(
            id="abc", slang="Break a leg", origin="Western",
            explanation="Good luck", panel_count=4,
            comic_url="/data/comics/x.png", thumbnail_url="/data/comics/x_thumb.png",
            comic_prompt="A 4-panel comic...", created_at="2026-04-01T00:00:00Z",
        )
        assert item.slang == "Break a leg"
