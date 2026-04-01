from pydantic import BaseModel, Field


class Panel(BaseModel):
    """A single comic panel description."""
    scene: str = Field(..., description="Visual scene description for this panel")
    dialogue: str = Field("", description="Dialogue or narration text for this panel")


class ScriptData(BaseModel):
    """Slang + comic script data returned by LLM."""
    slang: str = Field(..., description="The slang or idiom")
    origin: str = Field(..., description="Cultural origin (Eastern/Western)")
    explanation: str = Field(..., description="Brief explanation of the slang")
    panel_count: int = Field(..., ge=4, le=6, description="Number of panels (4-6)")
    panels: list[Panel] = Field(..., min_length=4, max_length=6, description="Panel descriptions")


class ScriptRequest(BaseModel):
    """Script generation request. Currently empty, reserved for future parameters."""
    model_config = {"extra": "forbid"}


class ScriptResponse(BaseModel):
    """Script generation response data."""
    slang: str
    origin: str
    explanation: str
    panel_count: int
    panels: list[Panel]
