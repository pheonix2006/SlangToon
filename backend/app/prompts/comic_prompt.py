"""Build visual prompt for Qwen Image 2.0 from comic script data."""

import tiktoken

# Qwen Image 2.0 token hard limit: 1000 tokens.
# Leave 50-token safety margin to avoid truncation.
MAX_PROMPT_TOKENS = 950


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in text using tiktoken."""
    if not text:
        return 0
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


def _truncate_prompt_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    """Truncate text to at most max_tokens tokens, preserving complete tokens."""
    if not text:
        return ""
    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)


def _get_layout(panel_count: int) -> str:
    """Return layout description for the given panel count."""
    layouts = {
        3: "1x3 grid (1 row, 3 columns)",
        4: "2x2 grid (2 rows, 2 columns)",
        5: "2+3 grid (2 top, 3 bottom)",
        6: "2x3 grid (2 rows, 3 columns)",
    }
    return layouts.get(panel_count, f"{panel_count}-panel grid")


def _build_panel_lines(
    panels: list[dict],
    max_scene: int,
    max_dialogue: int | None,
) -> list[str]:
    """Build panel description lines with clean truncation (no ellipsis markers)."""
    lines = []
    for i, panel in enumerate(panels, 1):
        scene = panel.get("scene", "")
        dialogue = panel.get("dialogue", "").strip()

        # Clean truncation — never add "..." markers
        if len(scene) > max_scene:
            scene = scene[:max_scene]

        line = f"P{i}: {scene}"
        if dialogue:
            if max_dialogue is not None and len(dialogue) > max_dialogue:
                dialogue = dialogue[:max_dialogue]
            line += f". {dialogue}"
        lines.append(line)
    return lines


def _try_prompt_tokens(panels: list[dict], header: str, footer: str,
                       max_scene: int, max_dialogue: int | None) -> str | None:
    """Build prompt with given compression level; return it if within token budget, else None."""
    lines = _build_panel_lines(panels, max_scene, max_dialogue)
    panels_text = " ".join(lines)
    prompt = header + panels_text + footer
    if count_tokens(prompt) <= MAX_PROMPT_TOKENS:
        return prompt
    return None


def build_comic_prompt(
    slang: str,
    origin: str,
    explanation: str,
    panels: list[dict],
    has_reference_image: bool = False,
) -> str:
    """Build a visual prompt within Qwen Image 2.0's 1000-token limit.

    Strategy: keep full dialogue whenever possible — compress scene
    descriptions first, only trim dialogue as a last resort. Never use
    "..." truncation markers that the model would render literally.
    """
    panel_count = len(panels)
    layout = _get_layout(panel_count)

    # Fixed parts of the prompt
    header = (
        f"A {panel_count}-panel {layout} manga comic strip, 16:9 landscape. "
        f'Title: "{slang}" ({origin}). All scenes in modern setting. '
    )
    character_guidance = ""
    if has_reference_image:
        character_guidance = (
            "The main character in all panels should resemble the person "
            "in the reference photo — same hairstyle, clothing, and general "
            "appearance, rendered in manga/comic style. "
        )
    full_header = header + character_guidance
    footer = (
        " Style: clean manga line art, warm colors, clear panel borders, "
        "white gutters, speech bubbles."
    )

    # Stage 1: full dialogue, progressively shrink scene descriptions
    scene_only_levels = [120, 80, 60, 40]
    for max_scene in scene_only_levels:
        result = _try_prompt_tokens(panels, full_header, footer, max_scene, None)
        if result:
            return result

    # Stage 2: also trim dialogue, keep generous dialogue budget
    dialogue_levels = [
        (40, 60),
        (30, 40),
        (25, 30),
        (20, 20),
        (15, 15),
    ]
    for max_scene, max_dialogue in dialogue_levels:
        result = _try_prompt_tokens(panels, full_header, footer, max_scene, max_dialogue)
        if result:
            return result

    # Stage 3: hard token truncation as last resort
    lines = _build_panel_lines(panels, 15, 15)
    panels_text = " ".join(lines)
    prompt = full_header + panels_text + footer
    return _truncate_prompt_to_tokens(prompt, MAX_PROMPT_TOKENS)
