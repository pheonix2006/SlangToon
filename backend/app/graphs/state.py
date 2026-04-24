"""LangGraph workflow shared state definition."""

from typing import Annotated, TypedDict
from operator import add


class WorkflowState(TypedDict, total=False):
    """LangGraph workflow shared state.

    Both ScriptGraph and ComicGraph share this State.
    total=False allows fields to be missing in initial state.
    """

    # -- Input --
    trigger: str  # trigger type (reserved for extension)
    reference_image: str  # 观众照片 base64（可选，图生图时使用）
    theme_id: str  # theme pack id (optional)
    theme_name_zh: str  # theme pack Chinese name (optional)

    # -- Script stage (script_node output) --
    slang: str
    origin: str
    explanation: str
    panel_count: int
    panels: list[dict]  # [{scene, dialogue, narration}, ...]

    # -- Comic stage --
    comic_prompt: str  # prompt_node output
    image_base64: str  # comic_node output
    comic_url: str  # save_node output
    thumbnail_url: str  # save_node output
    history_id: str  # save_node output

    # -- Error collection (reducer: append instead of overwrite) --
    errors: Annotated[list[str], add]
