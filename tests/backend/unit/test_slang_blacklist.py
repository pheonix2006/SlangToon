"""SlangBlacklist unit tests."""
import json
from pathlib import Path

import pytest

from app.slang_blacklist import SlangBlacklist


@pytest.fixture
def blacklist_file(tmp_path):
    return str(tmp_path / "slang_blacklist.json")


@pytest.fixture
def blacklist(blacklist_file):
    return SlangBlacklist(blacklist_file, max_entries=50)


class TestAutoCreate:
    """B-01: 首次启动自动创建空文件"""

    def test_file_not_exists_creates_empty_on_add(self, blacklist_file):
        """文件不存在时 add() 自动创建"""
        svc = SlangBlacklist(blacklist_file)
        assert not Path(blacklist_file).exists()
        svc.add("Carpe Diem")
        assert Path(blacklist_file).exists()
        data = json.loads(Path(blacklist_file).read_text(encoding="utf-8"))
        assert data["entries"] == ["Carpe Diem"]
        assert "updated_at" in data

    def test_empty_load_returns_empty_list(self, blacklist_file):
        svc = SlangBlacklist(blacklist_file)
        assert svc.load() == []


class TestAddDedup:
    """B-02: 添加去重不重复"""

    def test_add_single_entry(self, blacklist):
        blacklist.add("Carpe Diem")
        assert blacklist.load() == ["Carpe Diem"]

    def test_add_duplicate_does_not_duplicate(self, blacklist):
        blacklist.add("Carpe Diem")
        blacklist.add("Carpe Diem")
        blacklist.add("Carpe Diem")
        assert blacklist.load() == ["Carpe Diem"]
        assert len(blacklist.load()) == 1

    def test_add_multiple_distinct(self, blacklist):
        blacklist.add("Carpe Diem")
        blacklist.add("Crossing the Rubicon")
        blacklist.add("Break a leg")
        entries = blacklist.load()
        assert len(entries) == 3
        assert "Carpe Diem" in entries
        assert "Crossing the Rubicon" in entries
        assert "Break a leg" in entries


class TestTruncation:
    """B-03: 数量上限截断"""

    def test_truncates_at_max_entries(self, tmp_path):
        bl_file = str(tmp_path / "bl.json")
        svc = SlangBlacklist(bl_file, max_entries=5)
        for i in range(7):
            svc.add(f"slang-{i:02d}")
        entries = svc.load()
        assert len(entries) == 5
        assert entries[0] == "slang-06"
        assert "slang-00" not in entries

    def test_exact_max_no_truncation(self, tmp_path):
        bl_file = str(tmp_path / "bl.json")
        svc = SlangBlacklist(bl_file, max_entries=3)
        for s in ["a", "b", "c"]:
            svc.add(s)
        assert svc.load() == ["c", "b", "a"]


class TestPersistence:
    """B-04: 进程重启后恢复"""

    def test_persists_across_restarts(self, tmp_path):
        bl_file = str(tmp_path / "bl.json")
        s1 = SlangBlacklist(bl_file)
        for s in ["Alpha", "Beta", "Gamma"]:
            s1.add(s)
        s2 = SlangBlacklist(bl_file)
        assert s2.load() == ["Gamma", "Beta", "Alpha"]


class TestContains:
    """B-05: contains 查询"""

    def test_contains_existing(self, blacklist):
        blacklist.add("Carpe Diem")
        assert blacklist.contains("Carpe Diem") is True

    def test_contains_missing(self, blacklist):
        blacklist.add("Carpe Diem")
        assert blacklist.contains("Never Added") is False

    def test_contains_empty(self, blacklist):
        assert blacklist.contains("Anything") is False


class TestCorruptionTolerance:
    """B-06: JSON 损坏容错"""

    def test_corrupted_json_returns_empty(self, blacklist_file, caplog):
        Path(blacklist_file).write_text("{invalid", encoding="utf-8")
        assert SlangBlacklist(blacklist_file).load() == []
        assert any("损坏" in r.message for r in caplog.records)

    def test_missing_entries_key_returns_empty(self, blacklist_file):
        Path(blacklist_file).write_text('{"other":[]}', encoding="utf-8")
        assert SlangBlacklist(blacklist_file).load() == []

    def test_add_recovers_from_corrupted(self, blacklist_file):
        Path(blacklist_file).write_text("BAD", encoding="utf-8")
        SlangBlacklist(blacklist_file).add("Recovery")
        assert SlangBlacklist(blacklist_file).load() == ["Recovery"]


class TestGetRecent:
    """get_recent 边界测试"""

    def test_default_limit(self, blacklist):
        for i in range(5):
            blacklist.add(f"s-{i}")
        assert len(blacklist.get_recent()) == 5

    def test_smaller_limit(self, blacklist):
        for i in range(10):
            blacklist.add(f"s-{i}")
        assert blacklist.get_recent(limit=3) == ["s-9", "s-8", "s-7"]

    def test_exceeds_available(self, blacklist):
        blacklist.add("only")
        assert blacklist.get_recent(limit=100) == ["only"]
