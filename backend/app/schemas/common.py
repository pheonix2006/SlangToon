from typing import Any, Optional
from pydantic import BaseModel


class ApiResponse(BaseModel):
    """统一响应信封"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    data: Optional[Any] = None


class ErrorCode:
    BAD_REQUEST = 40001
    SCRIPT_LLM_FAILED = 50001       # Script generation LLM call failed
    SCRIPT_LLM_INVALID = 50002      # Script response JSON parse failed
    COMIC_LLM_FAILED = 50003        # Comic prompt composition failed
    COMIC_LLM_INVALID = 50004       # Comic prompt response parse failed
    IMAGE_GEN_FAILED = 50005        # Qwen Image 2.0 generation failed
    IMAGE_DOWNLOAD_FAILED = 50006   # Image download from Qwen failed
    INTERNAL_ERROR = 50007
