from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT
from app.prompts.comic_prompt import build_comic_prompt, count_tokens, MAX_PROMPT_TOKENS


class TestScriptPrompt:
    def test_prompt_contains_key_instructions(self):
        assert "JSON" in SCRIPT_SYSTEM_PROMPT
        assert "8-12" in SCRIPT_SYSTEM_PROMPT
        assert "Eastern" in SCRIPT_SYSTEM_PROMPT
        assert "Western" in SCRIPT_SYSTEM_PROMPT
        assert "English" in SCRIPT_SYSTEM_PROMPT
        assert "concise" in SCRIPT_SYSTEM_PROMPT
        assert "50 words" in SCRIPT_SYSTEM_PROMPT
        assert "20 words" in SCRIPT_SYSTEM_PROMPT
        assert "Brevity is critical" in SCRIPT_SYSTEM_PROMPT

    def test_prompt_requests_correct_json_format(self):
        assert '"slang"' in SCRIPT_SYSTEM_PROMPT
        assert '"origin"' in SCRIPT_SYSTEM_PROMPT
        assert '"panels"' in SCRIPT_SYSTEM_PROMPT
        assert '"panel_count"' in SCRIPT_SYSTEM_PROMPT
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert CONDENSE_SYSTEM_PROMPT
        assert "JSON" in CONDENSE_SYSTEM_PROMPT


class TestBuildComicPrompt:
    def test_basic_prompt_generation(self):
        panels = [
            {"scene": "A cat sits on a windowsill", "dialogue": "Cat: Meow"},
            {"scene": "The cat sees a bird outside", "dialogue": ""},
            {"scene": "Cat chases the bird", "dialogue": "Narrator: The hunt begins"},
            {"scene": "Cat napping after failed chase", "dialogue": ""},
            {"scene": "Cat sits on a windowsill again", "dialogue": ""},
            {"scene": "The cat sees a bird outside", "dialogue": ""},
            {"scene": "Cat chases the bird again", "dialogue": ""},
            {"scene": "Cat napping after failed chase again", "dialogue": ""},
        ]
        prompt = build_comic_prompt(
            slang="Curiosity killed the cat",
            origin="Western proverb",
            explanation="Being too curious can lead to trouble",
            panels=panels,
        )
        assert "Curiosity killed the cat" in prompt
        assert "manga" in prompt
        assert "8-panel" in prompt
        assert "Cat: Meow" in prompt

    def test_prompt_within_token_limit(self):
        """Prompt must never exceed MAX_PROMPT_TOKENS (950, API limit 1000)."""
        panels = [
            {"scene": "x" * 200, "dialogue": "y" * 100}
        ] * 12
        prompt = build_comic_prompt(
            slang="test-slang", origin="test-origin", explanation="test",
            panels=panels,
        )
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS

    def test_all_panels_present_in_prompt(self):
        """Even with 12 panels, all should be mentioned (P1..P12)."""
        panels = [
            {"scene": f"Scene {i} description with some detail", "dialogue": f"Line {i}"}
            for i in range(1, 13)
        ]
        prompt = build_comic_prompt("test", "test", "test", panels)
        for i in range(1, 13):
            assert f"P{i}:" in prompt, f"Panel {i} missing from prompt"

    def test_layout_description_varies_by_panel_count(self):
        p8 = [{"scene": "x", "dialogue": ""}] * 8
        p9 = [{"scene": "x", "dialogue": ""}] * 9
        p12 = [{"scene": "x", "dialogue": ""}] * 12

        prompt8 = build_comic_prompt("s", "o", "e", p8)
        prompt9 = build_comic_prompt("s", "o", "e", p9)
        prompt12 = build_comic_prompt("s", "o", "e", p12)

        assert "2x4 grid" in prompt8
        assert "3x3 grid" in prompt9
        assert "3x4 grid (3 rows" in prompt12

    def test_dialogue_truncation(self):
        panels = [{"scene": "short", "dialogue": "a" * 100}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS
        # Verify dialogue is still present after truncation
        assert "P1:" in prompt

    def test_scene_truncation(self):
        panels = [{"scene": "a" * 200, "dialogue": ""}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS

    def test_progressive_compression_with_many_panels(self):
        """12 panels with long text should still fit via progressive compression."""
        panels = [
            {
                "scene": "A detailed visual description of a complex modern scene with multiple characters",
                "dialogue": "Character says something important about the plot development",
            }
            for _ in range(12)
        ]
        prompt = build_comic_prompt(
            slang="塞翁失马",
            origin="Chinese, Warring States period",
            explanation="Blessing in disguise",
            panels=panels,
        )
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS
        # All 12 panels should still be present
        for i in range(1, 13):
            assert f"P{i}:" in prompt


class TestCountTokens:
    def test_count_tokens_basic(self):
        """count_tokens should return a positive integer for non-empty text."""
        from app.prompts.comic_prompt import count_tokens

        result = count_tokens("Hello, world!")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_empty(self):
        """count_tokens should return 0 for empty string."""
        from app.prompts.comic_prompt import count_tokens

        assert count_tokens("") == 0

    def test_count_tokens_approximate_accuracy(self):
        """count_tokens result should be roughly proportional to text length."""
        from app.prompts.comic_prompt import count_tokens

        short = count_tokens("cat")
        long = count_tokens("The quick brown fox jumps over the lazy dog " * 10)
        assert 0 < short < long

    def test_count_tokens_custom_encoding(self):
        """count_tokens should accept a custom encoding_name parameter."""
        from app.prompts.comic_prompt import count_tokens

        result = count_tokens("Hello", encoding_name="p50k_base")
        assert isinstance(result, int)
        assert result > 0


class TestMaxPromptTokensConstant:
    def test_max_prompt_tokens_value(self):
        """MAX_PROMPT_TOKENS should be 950 (1000 - 50 safety margin)."""
        from app.prompts.comic_prompt import MAX_PROMPT_TOKENS

        assert MAX_PROMPT_TOKENS == 950

    def test_max_prompt_tokens_less_than_hard_limit(self):
        """MAX_PROMPT_TOKENS must be strictly less than Qwen's 1000-token hard limit."""
        from app.prompts.comic_prompt import MAX_PROMPT_TOKENS

        assert MAX_PROMPT_TOKENS < 1000


class TestCondensePrompt:
    def test_prompt_exists_and_non_empty(self):
        """CONDENSE_SYSTEM_PROMPT should exist and be non-empty."""
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert CONDENSE_SYSTEM_PROMPT
        assert len(CONDENSE_SYSTEM_PROMPT.strip()) > 0

    def test_prompt_contains_role_definition(self):
        """CONDENSE_SYSTEM_PROMPT should define the comic script editor role."""
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert "comic script editor" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_contains_condensing_rules(self):
        """CONDENSE_SYSTEM_PROMPT should contain word count rules."""
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert "30 words" in CONDENSE_SYSTEM_PROMPT
        assert "12 words" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_preserves_fields(self):
        """CONDENSE_SYSTEM_PROMPT should say to keep slang, origin, explanation unchanged."""
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert "slang" in CONDENSE_SYSTEM_PROMPT
        assert "origin" in CONDENSE_SYSTEM_PROMPT
        assert "explanation" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_requests_json_format(self):
        """CONDENSE_SYSTEM_PROMPT should require JSON response."""
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        assert "JSON" in CONDENSE_SYSTEM_PROMPT
