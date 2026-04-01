from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 编码的图片", min_length=1, max_length=5_000_000)
    image_format: str = Field(default="jpeg", description="图片格式", pattern=r"^(jpeg|png|webp)$")


class StyleOption(BaseModel):
    name: str = Field(..., description="主题名称（中文2-6字）")
    brief: str = Field(..., description="一句话卖点（中文30字以内）")


class AnalyzeResponse(BaseModel):
    options: list[StyleOption] = Field(..., description="主题选项列表", min_length=5, max_length=5)
