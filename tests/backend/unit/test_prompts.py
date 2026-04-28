from app.prompts.script_prompt import SCRIPT_SYSTEM_PROMPT_TEMPLATE, build_system_prompt
from app.prompts.comic_prompt import build_comic_prompt, count_tokens, MAX_PROMPT_TOKENS


class TestScriptPrompt:
    def test_prompt_contains_key_instructions(self):
        assert "JSON" in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert "panel_count" in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert "English" in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert "visual storytelling" in SCRIPT_SYSTEM_PROMPT_TEMPLATE

    def test_prompt_allows_flexible_panel_count(self):
        assert "3 to 6" in SCRIPT_SYSTEM_PROMPT_TEMPLATE

    def test_prompt_requests_correct_json_format(self):
        assert '"slang"' in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert '"origin"' in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert '"panels"' in SCRIPT_SYSTEM_PROMPT_TEMPLATE
        assert '"panel_count"' in SCRIPT_SYSTEM_PROMPT_TEMPLATE
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
        assert "2x2" in prompt
        assert "16:9" in prompt
        assert "Cat: Meow" in prompt

    def test_prompt_within_token_limit(self):
        panels = [
            {"scene": "x" * 200, "dialogue": "y" * 100}
        ] * 4
        prompt = build_comic_prompt(
            slang="test-slang", origin="test-origin", explanation="test",
            panels=panels,
        )
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS

    def test_all_panels_present_in_prompt(self):
        panels = [
            {"scene": f"Scene {i} description with some detail", "dialogue": f"Line {i}"}
            for i in range(1, 5)
        ]
        prompt = build_comic_prompt("test", "test", "test", panels)
        for i in range(1, 5):
            assert f"P{i}:" in prompt, f"Panel {i} missing from prompt"

    def test_layout_description_for_4_panels(self):
        p4 = [{"scene": "x", "dialogue": ""}] * 4
        prompt = build_comic_prompt("s", "o", "e", p4)
        assert "2x2 grid" in prompt
        assert "16:9" in prompt

    def test_dialogue_truncation(self):
        panels = [{"scene": "short", "dialogue": "a" * 100}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS
        assert "P1:" in prompt

    def test_scene_truncation(self):
        panels = [{"scene": "a" * 200, "dialogue": ""}]
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS

    def test_progressive_compression_with_4_panels(self):
        panels = [
            {
                "scene": "A detailed visual description of a complex modern scene with multiple characters",
                "dialogue": "Character says something important about the plot development",
            }
            for _ in range(4)
        ]
        prompt = build_comic_prompt(
            slang="塞翁失马",
            origin="Chinese, Warring States period",
            explanation="Blessing in disguise",
            panels=panels,
        )
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS
        for i in range(1, 5):
            assert f"P{i}:" in prompt

    def test_with_reference_image_adds_character_guidance(self):
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
            has_reference_image=True,
        )
        assert "reference photo" in prompt
        assert "hairstyle" in prompt
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS

    def test_without_reference_image_no_character_guidance(self):
        panels = [
            {"scene": "A cat sits on a windowsill", "dialogue": "Cat: Meow"},
            {"scene": "The cat sees a bird outside", "dialogue": ""},
            {"scene": "Cat chases the bird", "dialogue": ""},
            {"scene": "Cat napping", "dialogue": ""},
        ]
        prompt = build_comic_prompt(
            slang="test",
            origin="test",
            explanation="test",
            panels=panels,
            has_reference_image=False,
        )
        assert "reference photo" not in prompt

    def test_default_has_reference_image_is_false(self):
        panels = [{"scene": "x", "dialogue": ""}] * 4
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert "reference photo" not in prompt

    def test_visual_style_replaces_default_footer(self):
        """When visual_style is provided, it replaces the default manga footer."""
        panels = [{"scene": "x", "dialogue": ""}] * 4
        prompt = build_comic_prompt(
            "s", "o", "e", panels,
            visual_style="Neon cyberpunk art with glowing lights",
        )
        assert "Neon cyberpunk art with glowing lights" in prompt
        assert "clean manga line art" not in prompt

    def test_empty_visual_style_uses_default_footer(self):
        """When visual_style is empty string, default manga footer is used."""
        panels = [{"scene": "x", "dialogue": ""}] * 4
        prompt = build_comic_prompt("s", "o", "e", panels, visual_style="")
        assert "clean manga line art" in prompt

    def test_no_visual_style_uses_default_footer(self):
        """When visual_style is not provided, default manga footer is used."""
        panels = [{"scene": "x", "dialogue": ""}] * 4
        prompt = build_comic_prompt("s", "o", "e", panels)
        assert "clean manga line art" in prompt

    def test_visual_style_within_token_limit(self):
        """Prompt with custom visual_style should still be within token limit."""
        panels = [
            {"scene": "x" * 200, "dialogue": "y" * 100}
        ] * 4
        prompt = build_comic_prompt(
            "s", "o", "e", panels,
            visual_style="Some very long visual style description " * 10,
        )
        assert count_tokens(prompt) <= MAX_PROMPT_TOKENS


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


class TestBuildSystemPrompt:
    """P-01~P-03: build_system_prompt 黑名单注入测试"""

    def test_empty_blacklist_returns_template_without_blacklist(self):
        """P-01: 空黑名单返回模板 prompt，无黑名单区块"""
        result = build_system_prompt([])
        assert "JSON" in result
        assert "3 to 6" in result
        assert "DO NOT pick" not in result

    def test_non_empty_blacklist_injects_section(self):
        """P-02: 有黑名单时注入已用俚语区块"""
        result = build_system_prompt(["Break a leg", "Curiosity killed the cat"])
        assert "DO NOT pick" in result
        assert "Break a leg" in result
        assert "Curiosity killed the cat" in result
        assert "DIFFERENT" in result

    def test_result_is_valid_complete_prompt_string(self):
        """P-03: 返回值是合法的完整 prompt 字符串"""
        result = build_system_prompt(["X"])
        assert isinstance(result, str)
        assert "JSON" in result
        assert "X" in result

    def test_single_item_blacklist(self):
        result = build_system_prompt(["Only one"])
        assert "1. Only one" in result
        assert "DO NOT pick" in result

    def test_many_items_blacklist(self):
        items = [f"Slang-{i}" for i in range(50)]
        result = build_system_prompt(items)
        for item in items:
            assert item in result

    def test_world_setting_injected_as_rule_5(self):
        """world_setting 出现时作为 rule 5 注入。"""
        result = build_system_prompt([], world_setting="A cyberpunk megacity")
        assert "5. The story is set in the following world: A cyberpunk megacity" in result
        assert "naturally fit this world" in result

    def test_world_setting_absent_no_extra_rule(self):
        """无 world_setting 时不注入额外规则。"""
        result = build_system_prompt([], world_setting="")
        assert "The story is set in the following world" not in result

    def test_world_setting_with_blacklist_numbering(self):
        """有 world_setting 时黑名单变为 rule 6。"""
        result = build_system_prompt(
            ["Old slang"],
            world_setting="A cyberpunk megacity",
        )
        assert "5. The story is set in the following world: A cyberpunk megacity" in result
        assert "6. DO NOT pick" in result
        assert "Old slang" in result

    def test_no_world_setting_blacklist_is_rule_5(self):
        """无 world_setting 时黑名单为 rule 5。"""
        result = build_system_prompt(["Old slang"])
        assert "5. DO NOT pick" in result
        assert "The story is set in the following world" not in result

    def test_world_setting_no_blacklist_only_rule_5(self):
        """有 world_setting 但无黑名单时只有 rule 5。"""
        result = build_system_prompt([], world_setting="Ancient Egypt")
        assert "5. The story is set in the following world: Ancient Egypt" in result
        assert "DO NOT pick" not in result
        assert "6. DO NOT" not in result
        assert "6. The story" not in result
