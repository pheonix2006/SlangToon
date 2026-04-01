"""Build visual prompt for Qwen Image 2.0 from comic script data."""

MAX_PROMPT_LENGTH = 800


def build_comic_prompt(
    slang: str,
    origin: str,
    explanation: str,
    panels: list[dict],
) -> str:
    """Build a concise visual prompt for generating a single 16:9 comic strip.

    The prompt must be within MAX_PROMPT_LENGTH characters (Qwen Image 2.0 limit).
    Each panel gets a brief scene description. Dialogue is included as speech bubble notes.
    """
    panel_count = len(panels)

    # Determine layout based on panel count
    if panel_count <= 3:
        layout = f"{panel_count}-panel horizontal row"
    elif panel_count == 4:
        layout = "4-panel horizontal row (2x2 grid also acceptable)"
    elif panel_count == 5:
        layout = "5-panel layout (3 on top row, 2 on bottom)"
    else:
        layout = "6-panel layout (3x2 grid)"

    # Build panel descriptions concisely
    panel_lines = []
    for i, panel in enumerate(panels, 1):
        scene = panel.get("scene", "")
        dialogue = panel.get("dialogue", "").strip()
        # Truncate scene if too long
        if len(scene) > 120:
            scene = scene[:117] + "..."
        line = f"Panel {i}: {scene}"
        if dialogue:
            if len(dialogue) > 60:
                dialogue = dialogue[:57] + "..."
            line += f". Speech: {dialogue}"
        panel_lines.append(line)

    panels_text = "\n".join(panel_lines)

    prompt = (
        f"A {layout} comic strip in manga style, 16:9 aspect ratio. "
        f"Title: \"{slang}\" ({origin}). {explanation}.\n\n"
        f"{panels_text}\n\n"
        f"Style: clean manga line art, expressive characters, warm color palette, "
        f"clear panel borders with white gutters, speech bubbles where dialogue is noted."
    )

    # Enforce character limit
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[: MAX_PROMPT_LENGTH - 3] + "..."

    return prompt
