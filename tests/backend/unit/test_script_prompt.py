"""System prompt language detection rule tests."""

from app.prompts.script_prompt import build_system_prompt


def test_prompt_contains_language_detection_rule():
    """System prompt must include language detection instructions."""
    prompt = build_system_prompt(blacklist=[], world_setting="")
    assert "Language Detection" in prompt or "LANGUAGE DETECTION" in prompt
    assert "Asian" in prompt
    assert "Chinese" in prompt or "中文" in prompt
    assert "English" in prompt
    assert "dialogue" in prompt.lower()


def test_prompt_language_rule_with_world_setting():
    """Language detection rule present even with world setting."""
    prompt = build_system_prompt(blacklist=[], world_setting="Cyberpunk city")
    assert "Language Detection" in prompt or "LANGUAGE DETECTION" in prompt
    assert "Cyberpunk" in prompt


def test_prompt_language_rule_with_blacklist():
    """Language detection rule present with blacklist."""
    prompt = build_system_prompt(blacklist=["Break a leg"], world_setting="")
    assert "Language Detection" in prompt or "LANGUAGE DETECTION" in prompt
    assert "Break a leg" in prompt
