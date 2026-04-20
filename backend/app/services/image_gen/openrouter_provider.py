"""OpenRouter provider — OpenAI-compatible image generation."""

from __future__ import annotations

import logging

import httpx

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)

# 大尺寸阈值：总像素 > 1K 默认分辨率 (1024*1024) 视为 2K
_2K_PIXEL_THRESHOLD = 1024 * 1024 + 1


class OpenRouterProvider:
    """基于 OpenRouter OpenAI 兼容接口的图像生成 provider。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        payload: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": self._convert_size(size),
        }
        logger.info("OpenRouter 文生图 (model=%s)", self._model)
        data = await self._request(payload)
        return self._parse_response(data)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — OpenRouter 不支持，抛出异常。"""
        raise ImageGenApiError(
            "OpenRouter does not support image-to-image generation"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_size(size: ImageSize) -> dict:
        """ImageSize → OpenRouter image_config dict。"""
        config: dict = {"aspect_ratio": size.aspect_ratio}
        if size.width * size.height > _2K_PIXEL_THRESHOLD:
            config["image_size"] = "2K"
        return config

    @staticmethod
    def _parse_response(api_response: dict) -> str:
        """解析 OpenRouter 响应，提取 base64 data URL。

        格式: choices[0].message.images[0].image_url.url
        """
        choices = api_response.get("choices", [])
        if not choices:
            raise ImageGenApiError(
                f"无法解析 OpenRouter 响应: {list(api_response.keys())}"
            )

        message = choices[0].get("message", {})
        images = message.get("images", [])
        if not images:
            raise ImageGenApiError(
                "OpenRouter 未返回图片，请确认模型支持图像生成且 modalities 参数正确"
            )

        return images[0]["image_url"]["url"]

    async def _request(self, payload: dict) -> dict:
        """发送请求到 OpenRouter，使用共享重试逻辑。"""
        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async def _do_request() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                return await client.post(url, json=payload, headers=headers)

        resp = await retry_with_backoff(
            _do_request,
            max_retries=self._max_retries,
            backoff_base=1.0,
        )
        return resp.json()
