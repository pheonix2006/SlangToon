"""Replicate provider 真实 API 验证脚本。

用法:
    uv run python tests/manual/test_replicate_real.py
    uv run python tests/manual/test_replicate_real.py --model openai/gpt-image-2 --extra '{"quality":"auto","moderation":"auto"}'
    uv run python tests/manual/test_replicate_real.py --i2i-only  # 仅测试图生图（需先有 t2i 结果图）

需要环境变量 REPLICATE_API_TOKEN（或 .env 中配置）。
默认使用 google/imagen-4 测试（便宜），可通过 --model 切换。
"""

import argparse
import asyncio
import base64
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.services.image_gen.base import ImageSize
from app.services.image_gen.replicate_provider import ReplicateProvider


T2I_PROMPT = (
    "A cute cartoon cat wearing a top hat, sitting on a stack of books, "
    "reading a newspaper. Bright colors, comic style, clean lines."
)

I2I_PROMPT = (
    "Transform this image into a watercolor painting style. "
    "Keep the same composition but make it look hand-painted with "
    "soft brush strokes and flowing colors."
)


def _save_and_report(label: str, result: str, filename: str, elapsed: float) -> bytes:
    assert result.startswith("data:image/"), f"unexpected prefix: {result[:50]}"
    raw_b64 = result.split(",", 1)[1]
    image_bytes = base64.b64decode(raw_b64)

    out_path = SCRIPT_DIR / filename
    out_path.write_bytes(image_bytes)

    print(f"\n  [OK] 耗时 {elapsed:.1f}s | 图片 {len(image_bytes):,} bytes")
    print(f"  [OK] 已保存: {out_path}")
    return image_bytes


async def test_text_to_image(provider: ReplicateProvider, model: str) -> str:
    size = ImageSize(2688, 1536)
    print(f"\n{'='*60}")
    print(f"[TEXT-TO-IMAGE] model={model}")
    print(f"  prompt:  {T2I_PROMPT[:80]}...")
    print(f"  size:    {size.width}x{size.height} ({size.aspect_ratio})")
    print(f"  params:  {provider._build_input('...', size)}")
    print(f"{'='*60}")

    t0 = time.monotonic()
    result = await provider.generate_from_text(T2I_PROMPT, size)
    elapsed = time.monotonic() - t0
    _save_and_report("T2I", result, "replicate_t2i_result.png", elapsed)
    return result


async def test_image_to_image(provider: ReplicateProvider, model: str, ref_b64: str) -> None:
    size = ImageSize(2688, 1536)
    print(f"\n{'='*60}")
    print(f"[IMAGE-TO-IMAGE] model={model}")
    print(f"  prompt:  {I2I_PROMPT[:80]}...")
    print(f"  ref:     data:image/...;base64, ({len(ref_b64)} chars)")
    print(f"  size:    {size.width}x{size.height} ({size.aspect_ratio})")
    print(f"{'='*60}")

    t0 = time.monotonic()
    result = await provider.generate(I2I_PROMPT, ref_b64, size)
    elapsed = time.monotonic() - t0
    _save_and_report("I2I", result, "replicate_i2i_result.png", elapsed)


def _load_ref_image() -> str | None:
    ref_path = SCRIPT_DIR / "replicate_t2i_result.png"
    if not ref_path.exists():
        return None
    raw = ref_path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Replicate provider 真实 API 验证")
    parser.add_argument("--model", default="google/imagen-4")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--extra", default="")
    parser.add_argument("--i2i-only", action="store_true", help="仅测试图生图")
    args = parser.parse_args()

    api_token = os.environ.get("REPLICATE_API_TOKEN", "")
    if not api_token:
        print("[ERROR] REPLICATE_API_TOKEN 未设置")
        sys.exit(1)

    print(f"Token: {api_token[:8]}...{api_token[-4:]}")
    print(f"Model: {args.model}")
    if args.extra:
        print(f"Extra: {args.extra}")

    provider = ReplicateProvider(
        api_key=api_token,
        model=args.model,
        timeout=float(args.timeout),
        max_retries=3,
        extra_params=args.extra,
    )

    failed = False

    if not args.i2i_only:
        try:
            t2i_result = await test_text_to_image(provider, args.model)
        except Exception as exc:
            print(f"\n  [FAIL] T2I: {type(exc).__name__}: {exc}")
            failed = True
            t2i_result = None
    else:
        t2i_result = None

    ref_b64 = t2i_result or _load_ref_image()
    if ref_b64:
        try:
            await test_image_to_image(provider, args.model, ref_b64)
        except Exception as exc:
            print(f"\n  [FAIL] I2I: {type(exc).__name__}: {exc}")
            failed = True
    else:
        print("\n  [SKIP] I2I: 无参考图（先运行 T2I 生成一张）")

    print(f"\n{'='*60}")
    if failed:
        print("[SOME TESTS FAILED]")
        sys.exit(1)
    print("[ALL PASSED]")


if __name__ == "__main__":
    asyncio.run(main())
