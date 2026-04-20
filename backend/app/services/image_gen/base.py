"""Image generation shared types, exceptions, and retry logic."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from math import gcd
from typing import Awaitable, Callable, Protocol

import httpx

logger = logging.getLogger(__name__)

# 常见标准宽高比（按浮点值从小到大排列），用于近似匹配。
_STANDARD_RATIOS: list[tuple[float, str]] = sorted(
    [
        (1 / 1, "1:1"),
        (9 / 16, "9:16"),
        (16 / 9, "16:9"),
        (3 / 4, "3:4"),
        (4 / 3, "4:3"),
        (2 / 3, "2:3"),
        (3 / 2, "3:2"),
        (4 / 5, "4:5"),
        (5 / 4, "5:4"),
        (21 / 9, "21:9"),
    ],
    key=lambda t: t[0],
)

# 近似匹配的容差（相对误差）
_RATIO_TOLERANCE = 0.02


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ImageGenApiError(Exception):
    """图像生成 API 返回错误。"""


class ImageGenTimeoutError(Exception):
    """图像生成请求超时。"""


# ---------------------------------------------------------------------------
# ImageSize
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageSize:
    """统一的图像尺寸表示，各 provider 自行转换为平台格式。"""

    width: int
    height: int

    @property
    def aspect_ratio(self) -> str:
        """返回简化的宽高比字符串，如 '9:16'。

        优先匹配常见标准比率（9:16、16:9、1:1 等），
        容差 2%；若无匹配则回退到 gcd 化简结果。
        """
        ratio_float = self.width / self.height
        for std_float, std_label in _STANDARD_RATIOS:
            if abs(ratio_float - std_float) / std_float <= _RATIO_TOLERANCE:
                return std_label
        d = gcd(self.width, self.height)
        return f"{self.width // d}:{self.height // d}"


# ---------------------------------------------------------------------------
# Provider Protocol
# ---------------------------------------------------------------------------

class ImageGenProvider(Protocol):
    """图像生成 provider 统一接口。"""

    async def generate_from_text(self, prompt: str, size: ImageSize) -> str:
        """文生图 — 返回 data:image/...;base64,... 格式字符串。"""
        ...

    async def generate(
        self, prompt: str, image_base64: str, size: ImageSize
    ) -> str:
        """图生图 — 返回 data:image/...;base64,... 格式字符串。"""
        ...


# ---------------------------------------------------------------------------
# Shared retry logic
# ---------------------------------------------------------------------------

async def retry_with_backoff(
    fn: Callable[[], Awaitable[httpx.Response]],
    *,
    max_retries: int = 3,
    backoff_base: float = 1.0,
) -> httpx.Response:
    """统一重试逻辑：5xx/连接错误重试，4xx 直接抛出，超时不重试。

    返回成功的 httpx.Response（2xx/3xx）。
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = await fn()

            if resp.status_code >= 500:
                last_exc = ImageGenApiError(
                    f"API 服务端错误 {resp.status_code}: {resp.text[:500]}"
                )
                logger.debug("5xx (attempt %d/%d): %s", attempt, max_retries, last_exc)
                if attempt < max_retries:
                    await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
                continue

            if resp.status_code >= 400:
                raise ImageGenApiError(
                    f"API 客户端错误 {resp.status_code}: {resp.text[:500]}"
                )

            return resp

        except httpx.TimeoutException as exc:
            raise ImageGenTimeoutError(
                f"请求超时: {exc}"
            ) from exc

        except (ImageGenApiError, ImageGenTimeoutError):
            raise

        except httpx.ConnectError as exc:
            last_exc = exc
            logger.debug("连接错误 (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))

        except Exception as exc:
            last_exc = exc
            logger.debug("请求异常 (attempt %d/%d): %s", attempt, max_retries, exc)
            if attempt < max_retries:
                await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))

    raise ImageGenApiError(
        f"请求在 {max_retries} 次重试后仍然失败"
    ) from last_exc
