from pydantic import BaseModel, Field

from app.schemas.script import Panel


class ComicRequest(BaseModel):
    """Comic generation request."""
    slang: str = Field(..., description="The slang being illustrated")
    origin: str = Field(..., description="Cultural origin of the slang")
    explanation: str = Field(..., description="Explanation of the slang")
    panel_count: int = Field(..., ge=3, le=6, description="Number of panels")
    panels: list[Panel] = Field(..., min_length=3, max_length=6, description="Panel descriptions")
    reference_image: str | None = Field(None, description="观众照片 base64 (data:image/...;base64,...)")
    theme_id: str = Field("", description="Theme pack ID for visual style lookup")


class ComicResponse(BaseModel):
    """Comic generation response data."""
    comic_url: str = Field(..., description="URL to the full comic image")
    thumbnail_url: str = Field(..., description="URL to the thumbnail")
    history_id: str = Field(..., description="Unique history record ID")
