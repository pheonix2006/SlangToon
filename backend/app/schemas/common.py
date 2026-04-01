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
    UNSUPPORTED_FORMAT = 40002
    IMAGE_TOO_LARGE = 40003
    VISION_LLM_FAILED = 50001
    VISION_LLM_INVALID = 50002
    IMAGE_GEN_FAILED = 50003
    IMAGE_DOWNLOAD_FAILED = 50004
    INTERNAL_ERROR = 50005
    COMPOSE_LLM_FAILED = 50006
    COMPOSE_LLM_INVALID = 50007
