"""Real API test: OpenRouter image-to-image with gallery-check.png."""

import asyncio
import base64
import os
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
_backend_dir = _project_root / "backend"
sys.path.insert(0, str(_backend_dir))
os.chdir(_backend_dir)

from app.config import get_settings
from app.services.image_gen.base import ImageSize
from app.services.image_gen.openrouter_provider import OpenRouterProvider


async def main() -> None:
    settings = get_settings()
    print(f"Model: {settings.openrouter_image_model}")

    provider = OpenRouterProvider(
        api_key=settings.openrouter_image_apikey,
        base_url=settings.openrouter_image_base_url,
        model=settings.openrouter_image_model,
        timeout=float(settings.openrouter_image_timeout),
        max_retries=2,
    )

    ref_path = _project_root / "gallery-check.png"
    ref_b64 = base64.b64encode(ref_path.read_bytes()).decode("ascii")
    ref_data_url = f"data:image/png;base64,{ref_b64}"
    print(f"Reference image: {ref_path.name} ({ref_path.stat().st_size} bytes)")

    print("\n[图生图] Sending request...")
    try:
        result = await provider.generate(
            "Transform this into a comic-style illustration, vibrant colors, bold outlines",
            ref_data_url,
            ImageSize(1024, 1024),
        )
        print(f"OK — data URL length: {len(result)}")
        out = _project_root / "tests" / "manual" / "i2i_result.png"
        prefix = result.index(",") + 1
        out.write_bytes(base64.b64decode(result[prefix:]))
        print(f"Saved: {out} ({out.stat().st_size} bytes)")
    except Exception as e:
        print(f"FAIL — {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
