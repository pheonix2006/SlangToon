"""Build visual prompt for Qwen Image 2.0 from comic script data."""

import tiktoken

# Qwen Image 2.0 text field hard limit: 800 characters.
# API auto-truncates anything beyond this. Leave 20-char safety margin.
MAX_PROMPT_LENGTH = 780

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
        8: "2x4 grid (2 rows, 4 columns)",
        9: "3x3 grid",
        10: "2x5 grid (2 rows, 5 columns)",
        11: "3x4 grid (last row 3 panels)",
        12: "3x4 grid (3 rows, 4 columns)",
    }
    return layouts.get(panel_count, f"{panel_count}-panel grid")


def _build_panel_lines(
    panels: list[dict],
    max_scene: int,
    max_dialogue: int,
) -> list[str]:
    """Build compact panel description lines."""
    lines = []
    for i, panel in enumerate(panels, 1):
        scene = panel.get("scene", "")
        dialogue = panel.get("dialogue", "").strip()
        # Truncate
        if len(scene) > max_scene:
            scene = scene[: max_scene - 3] + "..."
        line = f"P{i}: {scene}"
        if dialogue:
            if len(dialogue) > max_dialogue:
                dialogue = dialogue[: max_dialogue - 3] + "..."
            line += f'. "{dialogue}"'
        lines.append(line)
    return lines


def build_comic_prompt(
    slang: str,
    origin: str,
    explanation: str,
    panels: list[dict],
) -> str:
    """Build a compact visual prompt within Qwen Image 2.0's 800-char limit.

    Uses progressive compression: starts with fuller descriptions and reduces
    until the entire prompt fits within MAX_PROMPT_LENGTH.
    """
    panel_count = len(panels)
    layout = _get_layout(panel_count)

    # Fixed parts of the prompt
    header = f"A {panel_count}-panel {layout} manga comic strip, 16:9. " \
             f'Title: "{slang}" ({origin}). All scenes in modern setting. '
    footer = " Style: clean manga line art, warm colors, clear panel borders, white gutters, speech bubbles."

    # Calculate available budget for panel descriptions
    overhead = len(header) + len(footer)
    budget = MAX_PROMPT_LENGTH - overhead

    # Progressive compression: try decreasing truncation limits
    compression_levels = [
        (60, 30),   # Level 1: moderate compression
        (40, 20),   # Level 2: tight compression
        (25, 15),   # Level 3: heavy compression
        (15, 10),   # Level 4: ultra-compact
    ]

    panels_text = ""
    for max_scene, max_dialogue in compression_levels:
        lines = _build_panel_lines(panels, max_scene, max_dialogue)
        panels_text = " ".join(lines)
        if len(panels_text) <= budget:
            break
    else:
        # Last resort: scene-only, no dialogue, minimal text
        lines = [f"P{i}: {p.get('scene', '')[:20]}" for i, p in enumerate(panels, 1)]
        panels_text = " ".join(lines)
        if len(panels_text) > budget:
            panels_text = panels_text[: budget - 3] + "..."

    prompt = header + panels_text + footer

    # Final safety net
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[: MAX_PROMPT_LENGTH - 3] + "..."

    return prompt
