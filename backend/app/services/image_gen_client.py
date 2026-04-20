"""Backward-compatible image generation client.

Delegates to the provider selected by settings.image_gen_provider.
Preserves the original ImageGenClient interface and import paths so that
comic_node.py, routers/comic.py, and all existing tests continue to work.
"""

from __future__ import annotations

import logging

from langsmith import traceable

from app.config import Settings
from app.services.image_gen import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    create_image_gen_client,
)

logger = logging.getLogger(__name__)

# Re-export exceptions so existing `from app.services.image_gen_client import ...` works
__all__ = ["ImageGenClient", "ImageGenApiError", "ImageGenTimeoutError"]


class ImageGenClient:
    """向后兼容包装 — 委托给 provider 实现。

    保持与旧版完全相同的方法签名：
        generate_from_text(prompt, size="1536*2688") -> str
        generate(prompt, image_base64, image_format="jpeg", size="1024*1024") -> str
    """

    def __init__(self, settings: Settings) -> None:
        self._provider = create_image_gen_client(settings)
        self._provider_name = settings.image_gen_provider

    @traceable(run_type="tool", name="image_gen")
    async def generate_from_text(
        self,
        prompt: str,
        size: str = "1536*2688",
    ) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        image_size = self._parse_size(size)
        logger.info("ImageGenClient.generate_from_text (provider=%s)", self._provider_name)
        return await self._provider.generate_from_text(prompt, image_size)

    async def generate(
        self,
        prompt: str,
        image_base64: str,
        image_format: str = "jpeg",
        size: str = "1024*1024",
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 字符串。"""
        image_size = self._parse_size(size)
        logger.info("ImageGenClient.generate (provider=%s)", self._provider_name)
        return await self._provider.generate(prompt, image_base64, image_size)

    @staticmethod
    def _parse_size(size: str) -> ImageSize:
        """Parse 'W*H' string into ImageSize."""
        parts = size.split("*")
        if len(parts) != 2:
            raise ValueError(f"Invalid size format: '{size}', expected 'W*H'")
        return ImageSize(int(parts[0]), int(parts[1]))
