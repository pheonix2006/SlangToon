"""DashScope (Qwen Image 2.0) provider implementation."""

from __future__ import annotations

import base64
import logging

import httpx

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
    retry_with_backoff,
)

logger = logging.getLogger(__name__)


class DashScopeProvider:
    """基于 DashScope 同步接口的图像生成 provider。"""

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
        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]}
                ]
            },
            "parameters": {
                "n": 1,
                "size": self._convert_size(size),
                "prompt_extend": False,
            },
        }
        logger.info("DashScope 文生图 (model=%s)", self._model)
        data = await self._request(payload)
        image_url = self._parse_response(data)
        return await self._download_as_base64(image_url)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 字符串。"""
        clean_b64 = self._strip_data_prefix(image_base64)
        image_data_url = f"data:image/jpeg;base64,{clean_b64}"

        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_data_url},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {
                "n": 1,
                "size": self._convert_size(size),
            },
        }
        logger.info("DashScope 图生图 (model=%s)", self._model)
        data = await self._request(payload)
        image_url = self._parse_response(data)
        return await self._download_as_base64(image_url)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_size(size: ImageSize) -> str:
        """ImageSize → DashScope 格式 'WxH'。"""
        return f"{size.width}*{size.height}"

    @staticmethod
    def _parse_response(api_response: dict) -> str:
        """解析 DashScope 响应，提取图片 URL。

        支持同步格式 (output.choices) 和异步格式 (output.results)。
        """
        output = api_response.get("output", {})
        if isinstance(output, dict):
            # 同步格式: output.choices[0].message.content[0].image
            choices = output.get("choices", [])
            if isinstance(choices, list) and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", [])
                if isinstance(content, list) and len(content) > 0:
                    image_url = content[0].get("image", "")
                    if image_url:
                        return image_url

            # 异步格式: output.results[0].url
            results = output.get("results", [])
            if isinstance(results, list) and len(results) > 0:
                first = results[0]
                if isinstance(first, dict) and "url" in first:
                    return first["url"]

        raise ImageGenApiError(
            f"无法解析 DashScope 响应格式: {list(api_response.keys())}"
        )

    async def _request(self, payload: dict) -> dict:
        """发送请求到 DashScope，使用共享重试逻辑。"""
        url = f"{self._base_url}/services/aigc/multimodal-generation/generation"
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

    async def _download_as_base64(self, image_url: str) -> str:
        """下载远程图片并转为 base64 data URL。"""
        logger.info("下载图片: %s", image_url[:100])
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/png")
                b64 = base64.b64encode(resp.content).decode("ascii")
                logger.info("图片下载完成 (%d bytes)", len(resp.content))
                return f"data:{content_type};base64,{b64}"
        except httpx.HTTPStatusError as exc:
            raise ImageGenApiError(
                f"图片下载失败 (HTTP {exc.response.status_code})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ImageGenTimeoutError(
                f"图片下载超时 ({self._timeout}s)"
            ) from exc

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
