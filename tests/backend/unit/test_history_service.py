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
        record_id = service.add({"style_name": "cyberpunk", "prompt": "test prompt"})

        assert isinstance(record_id, str)
        assert len(record_id) > 0

    def test_add_auto_generates_id(self, service):
        id1 = service.add({"style_name": "a"})
        id2 = service.add({"style_name": "b"})

        assert id1 != id2

    def test_add_preserves_existing_id(self, service):
        custom_id = "my-custom-id"
        returned_id = service.add({"id": custom_id, "style_name": "a"})

        assert returned_id == custom_id

    def test_add_auto_generates_created_at(self, service):
        service.add({"style_name": "a"})

        records = service._load()
        assert "created_at" in records[0]
        assert records[0]["created_at"].endswith("Z") or "+" in records[0]["created_at"] or "T" in records[0]["created_at"]

    def test_add_preserves_existing_created_at(self, service):
        custom_time = "2026-01-01T00:00:00+00:00"
        service.add({"style_name": "a", "created_at": custom_time})

        records = service._load()
        assert records[0]["created_at"] == custom_time

    def test_add_inserts_at_front(self, service):
        service.add({"style_name": "first"})
        service.add({"style_name": "second"})
        service.add({"style_name": "third"})

        records = service._load()
        assert records[0]["style_name"] == "third"
        assert records[1]["style_name"] == "second"
        assert records[2]["style_name"] == "first"

    def test_add_truncates_to_max_records(self, tmp_path):
        history_file = str(tmp_path / "history.json")
        svc = HistoryService(history_file, max_records=3)

        svc.add({"style_name": "a"})
        svc.add({"style_name": "b"})
        svc.add({"style_name": "c"})
        svc.add({"style_name": "d"})  # should remove "a"

        records = svc._load()
        assert len(records) == 3
        assert records[0]["style_name"] == "d"
        assert records[-1]["style_name"] == "b"

    def test_add_creates_file_if_not_exists(self, history_file):
        svc = HistoryService(history_file)

        svc.add({"style_name": "first"})

        assert Path(history_file).exists()

    def test_add_preserves_all_fields(self, service):
        item = {
            "style_name": "cyberpunk",
            "prompt": "neon lights...",
            "poster_url": "/data/posters/x.png",
            "thumbnail_url": "/data/posters/x_thumb.png",
            "photo_url": "/data/photos/x.jpg",
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
            service.add({"style_name": f"style-{i}"})

        result = service.get_page()
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total"] == 5
        assert len(result["items"]) == 5

    def test_custom_page_size(self, service):
        for i in range(10):
            service.add({"style_name": f"s{i}"})

        result = service.get_page(page_size=3)
        assert len(result["items"]) == 3
        assert result["total"] == 10
        assert result["total_pages"] == 4  # ceil(10/3)

    def test_second_page(self, service):
        for i in range(5):
            service.add({"style_name": f"s{i}"})

        result = service.get_page(page=2, page_size=2)
        assert len(result["items"]) == 2
        assert result["items"][0]["style_name"] == "s2"  # newest first
        assert result["items"][1]["style_name"] == "s1"

    def test_page_beyond_total(self, service):
        service.add({"style_name": "only"})

        result = service.get_page(page=999)
        assert result["items"] == []
        assert result["total"] == 1

    def test_total_pages_calculation(self, service):
        for i in range(7):
            service.add({"style_name": f"s{i}"})

        assert service.get_page(page_size=3)["total_pages"] == 3  # ceil(7/3)
        assert service.get_page(page_size=5)["total_pages"] == 2  # ceil(7/5)
        assert service.get_page(page_size=10)["total_pages"] == 1

    def test_records_in_reverse_chronological_order(self, service):
        service.add({"style_name": "first"})
        service.add({"style_name": "second"})
        service.add({"style_name": "third"})

        result = service.get_page()
        names = [item["style_name"] for item in result["items"]]
        assert names == ["third", "second", "first"]

    def test_items_contain_required_fields(self, service):
        service.add({
            "style_name": "test",
            "prompt": "test prompt",
            "poster_url": "/poster.png",
            "thumbnail_url": "/thumb.png",
            "photo_url": "/photo.jpg",
        })

        result = service.get_page()
        item = result["items"][0]
        assert "id" in item
        assert "created_at" in item
        assert item["style_name"] == "test"
        assert item["prompt"] == "test prompt"
        assert item["poster_url"] == "/poster.png"
        assert item["thumbnail_url"] == "/thumb.png"
        assert item["photo_url"] == "/photo.jpg"
