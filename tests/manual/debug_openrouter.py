"""Quick debug: raw HTTP call to OpenRouter to see exact error."""

import asyncio
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.config import get_settings


async def main() -> None:
    s = get_settings()
    url = f"{s.openrouter_image_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {s.openrouter_image_apikey}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": s.openrouter_image_model,
        "messages": [{"role": "user", "content": "Draw a red circle"}],
        "modalities": ["image", "text"],
    }

    print(f"URL:   {url}")
    print(f"Model: {s.openrouter_image_model}")
    print(f"Key:   {s.openrouter_image_apikey[:12]}...")
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Body:   {resp.text[:2000]}")


if __name__ == "__main__":
    asyncio.run(main())
