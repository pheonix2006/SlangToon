"""Vision LLM 客户端 — OpenAI 兼容 API (GLM-4.6V 等)."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 自定义异常
# ---------------------------------------------------------------------------

class LLMTimeoutError(Exception):
    """LLM 请求超时且重试耗尽后抛出。"""


class LLMApiError(Exception):
    """LLM API 返回 4xx/5xx 错误。"""


class LLMResponseError(Exception):
    """LLM 返回内容无法解析或格式异常。"""


# ---------------------------------------------------------------------------
# 响应数据类
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """LLM response with content and usage metadata."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str | None = None

    @property
    def usage(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


# ---------------------------------------------------------------------------
# 客户端
# ---------------------------------------------------------------------------

class LLMClient:
    """基于 OpenAI 兼容接口的多模态 LLM 客户端。"""

    def __init__(self, settings: Settings) -> None:
        self._base_url: str = settings.openai_base_url.rstrip("/")
        self._api_key: str = settings.openai_api_key
        self._model: str = settings.openai_model
        self._max_tokens: int = settings.vision_llm_max_tokens
        self._timeout: float = float(settings.vision_llm_timeout)
        self._max_retries: int = settings.vision_llm_max_retries

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    async def chat_with_vision(
        self,
        system_prompt: str,
        image_base64: str,
        image_format: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """向 Vision LLM 发送图文请求并返回文本内容。

        超时 / 5xx 自动重试（指数退避），4xx 不重试直接抛出。
        """
        url = f"{self._base_url}/chat/completions"
        logger.info("LLM 请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(
            system_prompt=system_prompt,
            image_base64=image_base64,
            image_format=image_format,
            user_text=user_text,
            temperature=temperature,
        )

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = LLMApiError(
                            f"LLM API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.debug(
                            "Vision 请求 5xx (第 %d/%d 次): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    self._check_status(resp)

                    data = resp.json()
                    content: str = data["choices"][0]["message"]["content"]
                    logger.info("Vision 响应成功 (第 %d/%d 次)", attempt, self._max_retries)
                    usage = data.get("usage", {})
                    return LLMResponse(
                        content=content,
                        model=self._model,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                    )

            except httpx.TimeoutException as exc:
                last_exc = exc
                detail = repr(exc) if str(exc) else f"{type(exc).__name__}(timeout={self._timeout}s)"
                logger.debug(
                    "Vision 请求超时 (第 %d/%d 次): %s",
                    attempt, self._max_retries, detail,
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except LLMApiError as exc:
                # 4xx 不重试
                raise
            except Exception as exc:
                last_exc = exc
                logger.debug(
                    "Vision 请求异常 (第 %d/%d 次): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise LLMTimeoutError(
            f"Vision 请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc

    async def chat(
        self,
        system_prompt: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Text-only LLM call (no image). Same retry/backoff as chat_with_vision."""
        url = f"{self._base_url}/chat/completions"
        logger.info("文本请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "max_tokens": self._max_tokens,
            "temperature": temperature,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=payload, headers=headers)

                    if resp.status_code >= 500:
                        last_exc = LLMApiError(
                            f"LLM API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                        )
                        logger.debug(
                            "文本请求 5xx (第 %d/%d 次): %s",
                            attempt, self._max_retries, repr(last_exc),
                        )
                        if attempt < self._max_retries:
                            await self._backoff(attempt)
                        continue

                    self._check_status(resp)

                    data = resp.json()
                    content: str = data["choices"][0]["message"]["content"]
                    logger.info("文本响应成功 (第 %d/%d 次)", attempt, self._max_retries)
                    usage = data.get("usage", {})
                    return LLMResponse(
                        content=content,
                        model=self._model,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                    )

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.debug(
                    "文本请求超时 (第 %d/%d 次): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

            except LLMApiError:
                raise

            except Exception as exc:
                last_exc = exc
                logger.debug(
                    "文本请求异常 (第 %d/%d 次): %s",
                    attempt, self._max_retries, repr(exc),
                )
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        raise LLMTimeoutError(
            f"文本请求在 {self._max_retries} 次重试后仍然失败"
        ) from last_exc

    # ------------------------------------------------------------------
    # JSON 提取
    # ------------------------------------------------------------------

    @staticmethod
    def extract_json_from_content(content: str) -> dict:
        """从 LLM 返回的文本中提取 JSON 字典。

        支持以下格式：
        1. 纯 JSON 字符串
        2. 被 ```json ... ``` 包裹的 Markdown 代码块
        3. 被 ``` ... ``` 包裹的通用代码块
        """
        text = content.strip()

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 ```json ... ``` 中提取
        md_match = re.search(
            r"```(?:json)?\s*\n?(.*?)```",
            text,
            re.DOTALL,
        )
        if md_match:
            try:
                return json.loads(md_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        raise LLMResponseError(f"无法从 LLM 响应中提取有效 JSON: {content[:200]}")

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        system_prompt: str,
        image_base64: str,
        image_format: str,
        user_text: str,
        temperature: float,
    ) -> dict:
        # GLM-4.6V 要求 data URI 格式: data:image/<format>;base64,<data>
        if image_base64.startswith("data:"):
            image_url_value = image_base64
        else:
            image_url_value = f"data:image/{image_format};base64,{image_base64}"

        return {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url_value},
                        },
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
            "max_tokens": self._max_tokens,
            "temperature": temperature,
        }

    @staticmethod
    def _check_status(resp: httpx.Response) -> None:
        """检查响应状态码；4xx 转为 LLMApiError（5xx 由调用方处理）。"""
        if 400 <= resp.status_code < 500:
            body = resp.text[:500]
            raise LLMApiError(
                f"LLM API 错误 {resp.status_code}: {body}"
            )

    @staticmethod
    async def _backoff(attempt: int, base: float = 1.0) -> None:
        """指数退避等待。"""
        import asyncio
        delay = base * (2 ** (attempt - 1))
        await asyncio.sleep(delay)
