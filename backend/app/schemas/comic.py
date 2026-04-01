from pydantic import BaseModel, Field

from app.schemas.script import Panel


class ComicRequest(BaseModel):
    """Comic generation request."""
    slang: str = Field(..., description="The slang being illustrated")
    origin: str = Field(..., description="Cultural origin of the slang")
    explanation: str = Field(..., description="Explanation of the slang")
    panel_count: int = Field(..., ge=4, le=6, description="Number of panels")
    panels: list[Panel] = Field(..., min_length=4, max_length=6, description="Panel descriptions")


class ComicResponse(BaseModel):
    """Comic generation response data."""
    comic_url: str = Field(..., description="URL to the full comic image")
    thumbnail_url: str = Field(..., description="URL to the thumbnail")
    history_id: str = Field(..., description="Unique history record ID")
