from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    image_base64: str = Field(..., description="Base64 编码的原始照片", min_length=1)
    image_format: str = Field(default="jpeg", pattern=r"^(jpeg|png|webp)$")
    style_name: str = Field(..., description="选中的主题名称", min_length=1)
    style_brief: str = Field(..., description="选中的主题简述", min_length=1)


class GenerateResponse(BaseModel):
    poster_url: str = Field(..., description="海报图片的访问 URL")
    thumbnail_url: str = Field(..., description="缩略图访问 URL")
    history_id: str = Field(..., description="历史记录 ID")
