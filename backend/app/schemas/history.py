from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    id: str = Field(..., description="Unique record ID")
    slang: str = Field(..., description="The slang illustrated")
    origin: str = Field(..., description="Cultural origin")
    explanation: str = Field(..., description="Slang explanation")
    panel_count: int = Field(..., description="Number of comic panels")
    comic_url: str = Field(..., description="Comic image URL")
    thumbnail_url: str = Field(..., description="Thumbnail URL")
    comic_prompt: str = Field(..., description="Visual prompt sent to Qwen")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(..., description="Current page items")
    total: int = Field(..., description="Total record count")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total page count")
