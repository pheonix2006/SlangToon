import pytest

from app.prompts.analyze_prompt import ANALYZE_PROMPT
from app.prompts.compose_prompt import COMPOSE_PROMPT


def test_analyze_prompt_exists():
    """ANALYZE_PROMPT 应存在且非空"""
    assert ANALYZE_PROMPT
    assert len(ANALYZE_PROMPT) > 100


def test_analyze_prompt_contains_key_elements():
    """ANALYZE_PROMPT 应包含关键要素"""
    assert "5" in ANALYZE_PROMPT
    assert "options" in ANALYZE_PROMPT
    assert "name" in ANALYZE_PROMPT
    assert "brief" in ANALYZE_PROMPT
    # 不应包含旧的固定风格池
    assert "武侠江湖" not in ANALYZE_PROMPT


def test_compose_prompt_exists():
    """COMPOSE_PROMPT 应存在且非空"""
    assert COMPOSE_PROMPT
    assert len(COMPOSE_PROMPT) > 100


def test_compose_prompt_contains_key_elements():
    """COMPOSE_PROMPT 应包含关键维度"""
    assert "prompt" in COMPOSE_PROMPT
    assert "masterpiece" in COMPOSE_PROMPT
    assert "200-400" in COMPOSE_PROMPT
