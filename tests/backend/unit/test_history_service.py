"""HistoryService unit tests."""

import json
from pathlib import Path

import pytest

from app.services.history_service import HistoryService


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def history_file(tmp_path):
    return str(tmp_path / "history.json")


@pytest.fixture
def service(history_file):
    return HistoryService(history_file, max_records=100)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestAdd:
    def test_add_returns_id(self, service):
        record_id = service.add({"slang": "Break a leg", "comic_prompt": "test prompt"})

        assert isinstance(record_id, str)
        assert len(record_id) > 0

    def test_add_auto_generates_id(self, service):
        id1 = service.add({"slang": "Break a leg"})
        id2 = service.add({"slang": "Bite the bullet"})

        assert id1 != id2

    def test_add_preserves_existing_id(self, service):
        custom_id = "my-custom-id"
        returned_id = service.add({"id": custom_id, "slang": "Break a leg"})

        assert returned_id == custom_id

    def test_add_auto_generates_created_at(self, service):
        service.add({"slang": "Break a leg"})

        records = service._load()
        assert "created_at" in records[0]
        assert records[0]["created_at"].endswith("Z") or "+" in records[0]["created_at"] or "T" in records[0]["created_at"]

    def test_add_preserves_existing_created_at(self, service):
        custom_time = "2026-01-01T00:00:00+00:00"
        service.add({"slang": "Break a leg", "created_at": custom_time})

        records = service._load()
        assert records[0]["created_at"] == custom_time

    def test_add_inserts_at_front(self, service):
        service.add({"slang": "Break a leg"})
        service.add({"slang": "Bite the bullet"})
        service.add({"slang": "Under the weather"})

        records = service._load()
        assert records[0]["slang"] == "Under the weather"
        assert records[1]["slang"] == "Bite the bullet"
        assert records[2]["slang"] == "Break a leg"

    def test_add_truncates_to_max_records(self, tmp_path):
        history_file = str(tmp_path / "history.json")
        svc = HistoryService(history_file, max_records=3)

        svc.add({"slang": "Break a leg"})
        svc.add({"slang": "Bite the bullet"})
        svc.add({"slang": "Under the weather"})
        svc.add({"slang": "Spill the beans"})  # should remove "Break a leg"

        records = svc._load()
        assert len(records) == 3
        assert records[0]["slang"] == "Spill the beans"
        assert records[-1]["slang"] == "Bite the bullet"

    def test_add_creates_file_if_not_exists(self, history_file):
        svc = HistoryService(history_file)

        svc.add({"slang": "Break a leg"})

        assert Path(history_file).exists()

    def test_add_preserves_all_fields(self, service):
        item = {
            "slang": "Break a leg",
            "origin": "Western theater tradition",
            "explanation": "Used to wish good luck",
            "panel_count": 8,
            "comic_prompt": "A comic strip about wishing good luck before a stage performance...",
            "comic_url": "/data/comics/x.png",
            "thumbnail_url": "/data/comics/x_thumb.png",
        }
        service.add(item)

        records = service._load()
        for key, value in item.items():
            assert records[0][key] == value


# ---------------------------------------------------------------------------
# get_page
# ---------------------------------------------------------------------------

class TestGetPage:
    def test_empty_returns_empty_items(self, service):
        result = service.get_page()

        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 1

    def test_default_pagination(self, service):
        for i in range(5):
            service.add({"slang": f"slang-{i}"})

        result = service.get_page()
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total"] == 5
        assert len(result["items"]) == 5

    def test_custom_page_size(self, service):
        for i in range(10):
            service.add({"slang": f"slang-{i}"})

        result = service.get_page(page_size=3)
        assert len(result["items"]) == 3
        assert result["total"] == 10
        assert result["total_pages"] == 4  # ceil(10/3)

    def test_second_page(self, service):
        for i in range(5):
            service.add({"slang": f"slang-{i}"})

        result = service.get_page(page=2, page_size=2)
        assert len(result["items"]) == 2
        assert result["items"][0]["slang"] == "slang-2"  # newest first
        assert result["items"][1]["slang"] == "slang-1"

    def test_page_beyond_total(self, service):
        service.add({"slang": "Break a leg"})

        result = service.get_page(page=999)
        assert result["items"] == []
        assert result["total"] == 1

    def test_total_pages_calculation(self, service):
        for i in range(7):
            service.add({"slang": f"slang-{i}"})

        assert service.get_page(page_size=3)["total_pages"] == 3  # ceil(7/3)
        assert service.get_page(page_size=5)["total_pages"] == 2  # ceil(7/5)
        assert service.get_page(page_size=10)["total_pages"] == 1

    def test_records_in_reverse_chronological_order(self, service):
        service.add({"slang": "Break a leg"})
        service.add({"slang": "Bite the bullet"})
        service.add({"slang": "Under the weather"})

        result = service.get_page()
        names = [item["slang"] for item in result["items"]]
        assert names == ["Under the weather", "Bite the bullet", "Break a leg"]

    def test_items_contain_required_fields(self, service):
        service.add({
            "slang": "Break a leg",
            "origin": "Western theater tradition",
            "explanation": "Used to wish good luck",
            "panel_count": 8,
            "comic_prompt": "A comic strip about wishing good luck before a stage performance...",
            "comic_url": "/data/comics/x.png",
            "thumbnail_url": "/data/comics/x_thumb.png",
        })

        result = service.get_page()
        item = result["items"][0]
        assert "id" in item
        assert "created_at" in item
        assert item["slang"] == "Break a leg"
        assert item["origin"] == "Western theater tradition"
        assert item["explanation"] == "Used to wish good luck"
        assert item["panel_count"] == 8
        assert item["comic_prompt"] == "A comic strip about wishing good luck before a stage performance..."
        assert item["comic_url"] == "/data/comics/x.png"
        assert item["thumbnail_url"] == "/data/comics/x_thumb.png"
