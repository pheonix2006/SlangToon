"""Image generation multi-provider module.

Public API:
    create_image_gen_client() — factory function
    ImageGenApiError, ImageGenTimeoutError — exception types
    ImageSize — size value type
    ImageGenProvider — protocol for type hints
"""

from app.services.image_gen.base import (
    ImageGenApiError,
    ImageGenTimeoutError,
    ImageGenProvider,
    ImageSize,
)
from app.services.image_gen.factory import create_provider as create_image_gen_client

__all__ = [
    "create_image_gen_client",
    "ImageGenApiError",
    "ImageGenTimeoutError",
    "ImageGenProvider",
    "ImageSize",
]
