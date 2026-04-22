"""快速诊断 Replicate gpt-image-2 连通性。"""
import asyncio, sys, os, time, base64
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.services.image_gen.base import ImageSize
from app.services.image_gen.replicate_provider import ReplicateProvider


async def main():
    token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not token:
        print("[ERROR] REPLICATE_API_TOKEN 未设置")
        sys.exit(1)
    print(f"Token: {token[:8]}...{token[-4:]}")

    provider = ReplicateProvider(
        api_key=token,
        model="openai/gpt-image-2",
        timeout=180.0,
        max_retries=3,
        extra_params='{"quality":"auto","moderation":"auto","aspect_ratio":"3:2"}',
    )

    size = ImageSize(2688, 1536)
    params = provider._build_input("test", size)
    print(f"Params: {params}")

    print("开始 T2I 请求...")
    t0 = time.monotonic()
    try:
        result = await provider.generate_from_text(
            "A cute cartoon cat wearing a top hat, comic style",
            size,
        )
        elapsed = time.monotonic() - t0
        print(f"\n[OK] T2I 成功! {elapsed:.1f}s, {len(result)} chars")

        raw = base64.b64decode(result.split(",", 1)[1])
        out = PROJECT_ROOT / "tests/manual/output/replicate_gptimage2_result.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        print(f"[OK] 已保存: {out}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"\n[FAIL] {elapsed:.1f}s {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
