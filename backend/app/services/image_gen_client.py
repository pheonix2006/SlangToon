"""Qwen Image 2.0 图像生成客户端 — DashScope 同步接口."""

from __future__ import annotations

import base64
import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------

class ImageGenTimeoutError(Exception):
    """图像生成请求超时。"""


class ImageGenApiError(Exception):
    """图像生成 API 返回错误。"""


# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------

def parse_qwen_image_response(api_response: dict) -> str:
    """解析 Qwen Image 2.0 同步接口响应，提取图片 URL。

    响应格式：
    {
        "output": {
            "choices": [{
                "message": {
                    "content": [{"image": "https://..."}]
                }
            }]
        }
    }

    同时兼容 DashScope 异步接口格式：
    {
        "output": {"results": [{"url": "https://..."}]}
    }

    返回图片 URL 字符串。
    """
    # 同步接口格式: output.choices[0].message.content[0].image
    output = api_response.get("output", {})
    if isinstance(output, dict):
        choices = output.get("choices", [])
        if isinstance(choices, list) and len(choices) > 0:
            message = choices[0].get("message", {})
            content = message.get("content", [])
            if isinstance(content, list) and len(content) > 0:
                image_url = content[0].get("image", "")
                if image_url:
                    return image_url

        # 异步接口格式: output.results[0].url
        results = output.get("results", [])
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            if isinstance(first, dict) and "url" in first:
                return first["url"]

    raise ImageGenApiError(f"无法解析图像生成 API 响应格式: {list(api_response.keys())}")


# ---------------------------------------------------------------------------
# 客户端
# ---------------------------------------------------------------------------

class ImageGenClient:
    """基于 DashScope 同步接口的图像生成客户端。"""

    def __init__(self, settings: Settings) -> None:
        self._base_url: str = settings.qwen_image_base_url.rstrip("/")
        self._api_key: str = settings.qwen_image_apikey
        self._model: str = settings.qwen_image_model
        self._timeout: float = float(settings.qwen_image_timeout)
        self._max_retries: int = settings.qwen_image_max_retries

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        image_base64: str,
        image_format: str = "jpeg",
        size: str = "1024*1024",
    ) -> str:
        """图生图 — 提交 prompt + 参考图片，返回 base64 编码的生成结果。

        使用 DashScope 同步接口:
            POST /services/aigc/multimodal-generation/generation

        超时不重试（直接抛出），5xx / 连接错误重试。
        返回值是带 data:image/...;base64, 前缀的字符串。
        """
        url = f"{self._base_url}/services/aigc/multimodal-generation/generation"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # 构建 messages 格式的 payload
        clean_b64 = self._strip_data_prefix(image_base64)
        image_url_value = f"data:image/{image_format};base64,{clean_b64}"

        payload = {
            "model": self._model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_url_value},
                            {"text": prompt},
                        ],
                    }
                ]
            },
            "parameters": {
                "n": 1,
                "size": size,
            },
        }

        last_exc: Exception | None = None
        logger.info("图像生成请求发送中 (model=%s, timeout=%.0fs)", self._model, self._timeout)
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = ImageGenApiError(
                            f"图像生成 API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.warning(
                            "图像生成 5xx (attempt %d/%d): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    if resp.status_code >= 400:
                        raise ImageGenApiError(
                            f"图像生成 API 客户端错误 {resp.status_code}: {resp.text[:500]}"
                        )

                    data = resp.json()
                    image_url = parse_qwen_image_response(data)
                    logger.info("图像生成 API 响应成功 (attempt %d/%d)", attempt, self._max_retries)

                    # 下载图片 URL 并转为 base64
                    return await self._download_as_base64(image_url)

            except httpx.TimeoutException as exc:
                # 超时不重试
                raise ImageGenTimeoutError(
                    f"图像生成请求超时 ({self._timeout}s)"
                ) from exc

            except (ImageGenApiError, ImageGenTimeoutError):
                # 客户端错误 / 超时 — 已处理，直接抛出
                raise

            except httpx.ConnectError as exc:
                last_exc = exc
                logger.warning(
                    "图像生成连接错误 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "图像生成请求异常 (attempt %d/%d): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise ImageGenApiError(
            f"图像生成请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_data_prefix(data: str) -> str:
        """去除 ``data:image/...;base64,`` 前缀。"""
        prefix = "data:image/"
        idx = data.find(prefix)
        if idx != -1:
            # 找到逗号分隔符
            comma = data.find(",", idx)
            if comma != -1:
                return data[comma + 1:]
        return data

    async def _download_as_base64(self, image_url: str) -> str:
        """下载远程图片并转为 base64 字符串。"""
        logger.info("下载生成图片: %s", image_url[:100])
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/png")
            b64 = base64.b64encode(resp.content).decode("ascii")
            logger.info("图片下载完成 (size=%d bytes)", len(resp.content))
            return f"data:{content_type};base64,{b64}"

    @staticmethod
    async def _backoff(attempt: int, base: float = 1.0) -> None:
        """指数退避等待。"""
        import asyncio
        delay = base * (2 ** (attempt - 1))
        await asyncio.sleep(delay)
