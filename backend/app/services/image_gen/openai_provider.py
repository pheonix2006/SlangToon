"""OpenAI provider — OpenAI Images API (gpt-image-1)."""

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

_SIZE_MAP = {
    "1:1": "1024x1024",
    "16:9": "1536x1024",
    "9:16": "1024x1536",
}
_DEFAULT_SIZE = "1024x1024"


class OpenAIProvider:
    """基于 OpenAI Images API 的图像生成 provider。"""

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

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/png;base64,... 字符串。"""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "n": 1,
            "size": self._convert_size(size),
            "response_format": "b64_json",
        }
        logger.info("OpenAI 文生图 (model=%s)", self._model)
        data = await self._request("/images/generations", payload)
        return self._parse_response(data)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 通过 images/edits 传入参考图。"""
        clean_b64 = self._strip_data_prefix(image_base64)
        payload = {
            "model": self._model,
            "prompt": prompt,
            "image": clean_b64,
            "n": 1,
            "size": self._convert_size(size),
            "response_format": "b64_json",
        }
        logger.info("OpenAI 图生图 (model=%s)", self._model)
        data = await self._request("/images/edits", payload)
        return self._parse_response(data)

    @staticmethod
    def _convert_size(size: ImageSize) -> str:
        """ImageSize → OpenAI size 字符串。"""
        return _SIZE_MAP.get(size.aspect_ratio, _DEFAULT_SIZE)

    @staticmethod
    def _parse_response(api_response: dict) -> str:
        """解析 OpenAI Images API 响应。"""
        data_list = api_response.get("data", [])
        if not data_list:
            raise ImageGenApiError(
                f"无法解析 OpenAI 响应: {list(api_response.keys())}"
            )
        b64 = data_list[0].get("b64_json", "")
        if not b64:
            raise ImageGenApiError("OpenAI 未返回图片数据")
        return f"data:image/png;base64,{b64}"

    @staticmethod
    def _strip_data_prefix(data: str) -> str:
        """去除 data:image/...;base64, 前缀。"""
        prefix = "data:image/"
        idx = data.find(prefix)
        if idx != -1:
            comma = data.find(",", idx)
            if comma != -1:
                return data[comma + 1:]
        return data

    @staticmethod
    def _ensure_data_url(image_base64: str) -> str:
        if image_base64.startswith("data:image/"):
            return image_base64
        return f"data:image/jpeg;base64,{image_base64}"

    async def _request(self, endpoint: str, payload: dict) -> dict:
        """发送请求到 OpenAI API。"""
        url = f"{self._base_url}{endpoint}"
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
