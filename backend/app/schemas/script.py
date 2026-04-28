from pydantic import BaseModel, Field, model_validator


class Panel(BaseModel):
    """A single comic panel description."""
    scene: str = Field(..., description="Visual scene description for this panel")
    dialogue: str = Field("", description="Dialogue or narration text for this panel")


class ScriptData(BaseModel):
    """Slang + comic script data returned by LLM."""
    slang: str = Field(..., description="The slang or idiom")
    origin: str = Field(..., description="Cultural origin (Eastern/Western)")
    explanation: str = Field(..., description="Brief explanation of the slang")
    panel_count: int = Field(..., ge=3, le=6, description="Number of panels (3-6)")
    panels: list[Panel] = Field(..., min_length=3, max_length=6, description="Panel descriptions")

    @model_validator(mode="after")
    def check_panel_count_matches(self) -> "ScriptData":
        """Ensure panel_count matches the actual number of panels."""
        if self.panel_count != len(self.panels):
            raise ValueError(
                f"panel_count ({self.panel_count}) does not match "
                f"number of panels ({len(self.panels)})"
            )
        return self


class ScriptRequest(BaseModel):
    """Script generation request."""
    model_config = {"extra": "forbid"}
    captured_image: str = ""


class ScriptResponse(BaseModel):
    """Script generation response data."""
    slang: str
    origin: str
    explanation: str
    panel_count: int
    panels: list[Panel]
    theme_id: str = ""
    theme_name_zh: str = ""
