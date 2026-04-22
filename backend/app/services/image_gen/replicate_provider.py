"""Replicate provider — 通用 Replicate 图像生成 (支持多模型)。"""

from __future__ import annotations

import asyncio
import base64
import json
import logging

import replicate as replicate_sdk

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageSize,
)

logger = logging.getLogger(__name__)


class ReplicateProvider:
    """基于 Replicate API 的图像生成 provider，支持多模型自动适配。

    通用参数仅 prompt + aspect_ratio（从 ImageSize 推导），
    其余全部由 extra_params (JSON) 注入，provider 本身不硬编码任何模型逻辑。
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float,
        max_retries: int,
        extra_params: str = "",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries
        self._extra_params = self._parse_extra_params(extra_params)

    @staticmethod
    def _parse_extra_params(raw: str) -> dict:
        if not raw or not raw.strip():
            return {}
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("extra_params must be a JSON object")
            return parsed
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("replicate_image_extra_params 解析失败，已忽略: %s", exc)
            return {}

    @staticmethod
    def _convert_size(size: ImageSize) -> str:
        """ImageSize → Replicate aspect_ratio 字符串。

        Replicate API 不接受像素尺寸，只接受 aspect_ratio。
        """
        return size.aspect_ratio

    def _build_input(self, prompt: str, size: ImageSize) -> dict:
        """构建请求参数：prompt + aspect_ratio + extra_params 合并。"""
        params: dict = {
            "prompt": prompt,
            "aspect_ratio": self._convert_size(size),
        }
        params.update(self._extra_params)
        return params

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 字符串。"""
        input_params = self._build_input(prompt, size)
        logger.info("Replicate 文生图 (model=%s)", self._model)
        return await self._run(input_params)

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 通过 input_images 传入参考图。"""
        image_url = self._ensure_data_url(image_base64)
        input_params = self._build_input(prompt, size)
        input_params["input_images"] = [image_url]
        logger.info("Replicate 图生图 (model=%s)", self._model)
        return await self._run(input_params)

    @staticmethod
    def _ensure_data_url(image_base64: str) -> str:
        if image_base64.startswith("data:image/"):
            return image_base64
        return f"data:image/jpeg;base64,{image_base64}"

    async def _run(self, input_params: dict) -> str:
        """调用 Replicate API 并返回 base64 data URL。"""
        client = replicate_sdk.Client(api_token=self._api_key)

        try:
            output = await asyncio.wait_for(
                asyncio.to_thread(client.run, self._model, input=input_params),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as exc:
            raise ImageGenTimeoutError(
                f"Replicate 请求超时 ({self._timeout}s)"
            ) from exc
        except Exception as exc:
            raise ImageGenApiError(
                f"Replicate API 调用失败: {exc}"
            ) from exc

        if not output:
            raise ImageGenApiError("Replicate 未返回图片")

        file_output = output[0] if isinstance(output, list) else output
        try:
            image_bytes = await asyncio.to_thread(file_output.read)
        except Exception as exc:
            raise ImageGenApiError(
                f"Replicate 图片下载失败: {exc}"
            ) from exc

        b64 = base64.b64encode(image_bytes).decode("ascii")
        logger.info("Replicate 图片生成完成 (%d bytes)", len(image_bytes))
        return f"data:image/png;base64,{b64}"
