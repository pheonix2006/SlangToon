"""Vision LLM 客户端 — OpenAI 兼容 API (GLM-4.6V 等)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

import httpx

from app.config import Settings
from langsmith import traceable

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


@dataclass
class StreamChunk:
    """流式输出的单个 chunk。"""

    type: str          # "thinking" | "content" | "done" | "error"
    text: str = ""
    reasoning: str = ""
    content: str = ""
    usage: dict = field(default_factory=dict)


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

    @traceable(run_type="llm", name="glm_chat_with_vision")
    async def chat_with_vision(
        self,
        system_prompt: str,
        image_base64: str,
        image_format: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """向 Vision LLM 发送图文请求（SSE 流式）。

        Streaming keeps the connection alive during long reasoning phases.
        超时 / 5xx 自动重试（指数退避），4xx 不重试直接抛出。
        """
        url = f"{self._base_url}/chat/completions"
        logger.info("Vision 流式请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
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
        payload["stream"] = True  # 启用 SSE 流式

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as resp:
                        if resp.status_code >= 500:
                            body = await resp.aread()
                            last_exc = LLMApiError(
                                f"LLM API 服务端错误 {resp.status_code}: {body[:500].decode(errors='replace')}"
                            )
                            logger.debug(
                                "Vision 请求 5xx (第 %d/%d 次): %s",
                                attempt, self._max_retries, repr(last_exc),
                            )
                            if attempt < self._max_retries:
                                await self._backoff(attempt)
                            continue

                        await self._check_status(resp)

                        result = await self._collect_stream(resp)
                        logger.info("Vision 流式响应成功 (第 %d/%d 次, content_len=%d)", attempt, self._max_retries, len(result["content"]))
                        return LLMResponse(
                            content=result["content"],
                            model=self._model,
                            prompt_tokens=result["usage"].get("prompt_tokens", 0),
                            completion_tokens=result["usage"].get("completion_tokens", 0),
                            total_tokens=result["usage"].get("total_tokens", 0),
                            finish_reason=result["finish_reason"],
                        )
                    # stream context manager exits here — safe point after full read

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

    @traceable(run_type="llm", name="glm_chat")
    async def chat(
        self,
        system_prompt: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> LLMResponse:
        """Text-only LLM call using SSE streaming.

        Streaming keeps the connection alive during long reasoning phases,
        preventing intermediate proxies / gateways from dropping idle connections.
        """
        url = f"{self._base_url}/chat/completions"
        logger.info("文本流式请求发送中 (url=%s, model=%s, timeout=%.0fs)", url, self._model, self._timeout)
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
            "stream": True,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as resp:
                        if resp.status_code >= 500:
                            body = await resp.aread()
                            last_exc = LLMApiError(
                                f"LLM API 服务端错误 {resp.status_code}: {body[:500].decode(errors='replace')}"
                            )
                            logger.debug(
                                "文本请求 5xx (第 %d/%d 次): %s",
                                attempt, self._max_retries, repr(last_exc),
                            )
                            if attempt < self._max_retries:
                                await self._backoff(attempt)
                            continue

                        await self._check_status(resp)

                        result = await self._collect_stream(resp)
                        logger.info("文本流式响应成功 (第 %d/%d 次, content_len=%d)", attempt, self._max_retries, len(result["content"]))
                        return LLMResponse(
                            content=result["content"],
                            model=self._model,
                            prompt_tokens=result["usage"].get("prompt_tokens", 0),
                            completion_tokens=result["usage"].get("completion_tokens", 0),
                            total_tokens=result["usage"].get("total_tokens", 0),
                            finish_reason=result["finish_reason"],
                        )
                    # stream context manager exits here — safe point after full read

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

    async def chat_stream(
        self,
        system_prompt: str,
        user_text: str,
        temperature: float = 0.8,
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式 LLM 调用，逐 chunk yield thinking/content/done。"""
        url = f"{self._base_url}/chat/completions"
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
            "stream": True,
        }

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    async with client.stream("POST", url, json=payload, headers=headers) as resp:
                        if resp.status_code >= 500:
                            body = await resp.aread()
                            last_exc = LLMApiError(f"LLM API 服务端错误 {resp.status_code}")
                            if attempt < self._max_retries:
                                await self._backoff(attempt)
                            continue
                        await self._check_status(resp)

                        reasoning_parts: list[str] = []
                        content_parts: list[str] = []
                        finish_reason: str | None = None
                        usage: dict = {}

                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            delta = chunk.get("choices", [{}])[0].get("delta", {})

                            if "reasoning_content" in delta:
                                text = delta["reasoning_content"]
                                reasoning_parts.append(text)
                                yield StreamChunk(type="thinking", text=text)

                            if "content" in delta:
                                text = delta["content"]
                                content_parts.append(text)
                                yield StreamChunk(type="content", text=text)

                            choice = chunk.get("choices", [{}])[0]
                            if choice.get("finish_reason"):
                                finish_reason = choice["finish_reason"]
                            if "usage" in chunk:
                                usage = chunk["usage"]

                        yield StreamChunk(
                            type="done",
                            reasoning="".join(reasoning_parts),
                            content="".join(content_parts),
                            usage=usage,
                        )
                        return

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await self._backoff(attempt)
            except LLMApiError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    await self._backoff(attempt)

        yield StreamChunk(type="error", text=f"请求在 {self._max_retries} 次重试后失败")

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
        4. JSON 前后混有解释文字
        5. 尾部逗号等常见 LLM 格式瑕疵
        """
        logger.debug("LLM 原始响应 (len=%d):\n%s", len(content), content)
        text = content.strip()

        # 策略 1: 直接解析
        result = _try_parse_json(text)
        if result is not None:
            return result

        # 策略 2: 从 ```json ... ``` / ``` ... ``` 代码块提取
        md_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if md_match:
            result = _try_parse_json(md_match.group(1).strip())
            if result is not None:
                return result

        # 策略 3: 提取第一个 { ... } 块（处理 JSON 前后有解释文字）
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            result = _try_parse_json(brace_match.group(0))
            if result is not None:
                return result

        raise LLMResponseError(
            f"无法从 LLM 响应中提取有效 JSON (len={len(content)}): {content[:500]}"
        )

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
    async def _check_status(resp: httpx.Response) -> None:
        """检查响应状态码；4xx 转为 LLMApiError（5xx 由调用方处理）。

        流式响应需先 aread() 才能访问 body。
        """
        if 400 <= resp.status_code < 500:
            body = (await resp.aread()).decode(errors="replace")[:500]
            raise LLMApiError(
                f"LLM API 错误 {resp.status_code}: {body}"
            )

    @staticmethod
    async def _collect_stream(resp: httpx.Response) -> dict:
        """从 SSE 流中收集完整响应内容。

        OpenAI 兼容格式：
          data: {"choices":[{"delta":{"content":"..."}}]}
          data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{...}}
          data: [DONE]
        """
        content_parts: list[str] = []
        finish_reason: str | None = None
        usage: dict = {}

        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]  # strip "data: " prefix
            if data_str.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if "content" in delta:
                content_parts.append(delta["content"])

            choice = chunk.get("choices", [{}])[0]
            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]
            if "usage" in chunk:
                usage = chunk["usage"]

        return {
            "content": "".join(content_parts),
            "finish_reason": finish_reason,
            "usage": usage,
        }

    @staticmethod
    async def _backoff(attempt: int, base: float = 1.0) -> None:
        """指数退避等待。"""
        import asyncio
        delay = base * (2 ** (attempt - 1))
        await asyncio.sleep(delay)


def _try_parse_json(text: str) -> dict | None:
    """尝试解析 JSON，容忍尾部逗号、未转义引号等常见 LLM 格式瑕疵。"""
    # 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 移除尾部逗号后重试: ,] → ] 和 ,} → }
    cleaned = re.sub(r",\s*([}\]])", r"\1", text)
    if cleaned != text:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
    # json-repair 兜底：处理未转义引号、缺失括号等
    try:
        from json_repair import repair_json
        result = repair_json(text, return_objects=True)
        if isinstance(result, dict):
            return result
    except Exception:
        pass
    return None
