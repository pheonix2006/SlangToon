from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.prompts.comic_prompt import build_comic_prompt, MAX_PROMPT_LENGTH


class TestScriptPrompt:
    def test_prompt_contains_key_instructions(self):
        assert "JSON" in SCRIPT_SYSTEM_PROMPT
        assert "4-6 panel" in SCRIPT_SYSTEM_PROMPT
        assert "Eastern" in SCRIPT_SYSTEM_PROMPT
        assert "Western" in SCRIPT_SYSTEM_PROMPT
        assert "English" in SCRIPT_SYSTEM_PROMPT

    def test_prompt_requests_correct_json_format(self):
        assert '"slang"' in SCRIPT_SYSTEM_PROMPT
        assert '"origin"' in SCRIPT_SYSTEM_PROMPT
        assert '"panels"' in SCRIPT_SYSTEM_PROMPT
        assert '"panel_count"' in SCRIPT_SYSTEM_PROMPT


class TestBuildComicPrompt:
    def test_basic_prompt_generation(self):
        panels = [
            {"scene": "A cat sits on a windowsill", "dialogue": "Cat: Meow"},
            {"scene": "The cat sees a bird outside", "dialogue": ""},
            {"scene": "Cat chases the bird", "dialogue": "Narrator: The hunt begins"},
            {"scene": "Cat napping after failed chase", "dialogue": ""},
        ]
        prompt = build_comic_prompt(
            slang="Curiosity killed the cat",
            origin="Western proverb",
            explanation="Being too curious can lead to trouble",
            panels=panels,
        )
        assert "Curiosity killed the cat" in prompt
        assert "manga" in prompt
        assert "4-panel" in prompt
        assert "Cat: Meow" in prompt

    def test_prompt_within_char_limit(self):
        panels = [{"scene": "x" * 200, "dialogue": "y" * 100}] * 6
        prompt = build_comic_prompt(
            slang="test", origin="test", explanation="test",
            panels=panels,
        )
        assert len(prompt) <= MAX_PROMPT_LENGTH

    def test_layout_description_varies_by_panel_count(self):
        p3 = [{"scene": "x", "dialogue": ""}] * 3
        p5 = [{"scene": "x", "dialogue": ""}] * 5
        p6 = [{"scene": "x", "dialogue": ""}] * 6

        prompt3 = build_comic_prompt("s", "o", "e", p3)
        prompt5 = build_comic_prompt("s", "o", "e", p5)
        prompt6 = build_comic_prompt("s", "o", "e", p6)

        assert "3-panel" in prompt3
        assert "5-panel" in prompt5
        assert "6-panel" in prompt6

    def test_dialogue_truncation(self):
        panels = [{"scene": "short", "dialogue": "a" * 100}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert len(prompt) <= MAX_PROMPT_LENGTH

    def test_scene_truncation(self):
        panels = [{"scene": "a" * 200, "dialogue": ""}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert "..." in prompt
        assert len(prompt) <= MAX_PROMPT_LENGTH
