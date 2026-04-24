"""Tests for theme_packs module."""

from app.prompts.theme_packs import (
    THEME_PACKS,
    get_random_theme,
    get_theme_by_id,
)


def test_theme_packs_count():
    assert len(THEME_PACKS) == 18


def test_theme_pack_structure():
    required_keys = {"id", "name_zh", "name_en", "world_setting", "visual_style"}
    for theme in THEME_PACKS:
        assert required_keys.issubset(set(theme.keys())), f"Missing keys in {theme['id']}"


def test_theme_ids_unique():
    ids = [t["id"] for t in THEME_PACKS]
    assert len(ids) == len(set(ids))


def test_get_random_theme_returns_valid():
    for _ in range(50):
        theme = get_random_theme()
        assert theme["id"] in [t["id"] for t in THEME_PACKS]


def test_get_theme_by_id_found():
    assert get_theme_by_id("cyberpunk") is not None
    assert get_theme_by_id("cyberpunk")["name_zh"] == "赛博朋克"


def test_get_theme_by_id_not_found():
    assert get_theme_by_id("nonexistent") is None
