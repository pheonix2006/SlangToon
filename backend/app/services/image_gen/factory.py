"""Factory for creating image generation providers based on config."""

from __future__ import annotations

from app.config import Settings
from app.services.image_gen.dashscope_provider import DashScopeProvider
from app.services.image_gen.openrouter_provider import OpenRouterProvider
from app.services.image_gen.replicate_provider import ReplicateProvider
from app.services.image_gen.openai_provider import OpenAIProvider


def create_provider(
    settings: Settings,
) -> DashScopeProvider | OpenRouterProvider | ReplicateProvider | OpenAIProvider:
    """根据 settings.image_gen_provider 创建对应的 provider 实例。"""
    name = settings.image_gen_provider.lower().strip()

    if name == "dashscope":
        return DashScopeProvider(
            api_key=settings.qwen_image_apikey,
            base_url=settings.qwen_image_base_url,
            model=settings.qwen_image_model,
            timeout=float(settings.qwen_image_timeout),
            max_retries=settings.qwen_image_max_retries,
        )

    if name == "openrouter":
        return OpenRouterProvider(
            api_key=settings.openrouter_image_apikey,
            base_url=settings.openrouter_image_base_url,
            model=settings.openrouter_image_model,
            timeout=float(settings.openrouter_image_timeout),
            max_retries=settings.openrouter_image_max_retries,
        )

    if name == "replicate":
        return ReplicateProvider(
            api_key=settings.replicate_api_token,
            model=settings.replicate_image_model,
            timeout=float(settings.replicate_image_timeout),
            max_retries=settings.replicate_image_max_retries,
            extra_params=settings.replicate_image_extra_params,
        )

    if name == "openai":
        return OpenAIProvider(
            api_key=settings.openai_image_apikey,
            base_url=settings.openai_image_base_url,
            model=settings.openai_image_model,
            timeout=float(settings.openai_image_timeout),
            max_retries=settings.openai_image_max_retries,
        )

    raise ValueError(
        f"Unknown image_gen_provider: '{settings.image_gen_provider}'. "
        f"Supported: 'dashscope', 'openrouter', 'replicate', 'openai'"
    )
