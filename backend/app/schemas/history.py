from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    id: str = Field(..., description="记录唯一 ID")
    style_name: str = Field(..., description="使用的风格名称")
    prompt: str = Field(..., description="使用的生图提示词")
    poster_url: str = Field(..., description="海报图片 URL")
    thumbnail_url: str = Field(..., description="缩略图 URL")
    photo_url: str = Field("", description="原始照片 URL")
    created_at: str = Field(..., description="创建时间 ISO 8601")


class HistoryResponse(BaseModel):
    items: list[HistoryItem] = Field(..., description="当前页记录列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")
