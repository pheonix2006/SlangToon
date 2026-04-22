"""完整流程对比测试 — Qwen / Gemini / OpenAI 三模型图生图效果对比。

用法:
    cd backend
    uv run python ../tests/manual/test_image_gen_comparison.py --image ../data/ccd6bcb3d0a579a2da643c7c49425bfb.jpg

输入: 一张测试照片（模拟观众 OK 手势后拍的照片）
输出: tests/manual/output/ 目录下三张结果图 + 控制台耗时对比
"""

import argparse
import asyncio
import base64
import logging
import sys
import time
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))

from app.config import Settings
from app.dependencies import get_cached_settings
from app.graphs.comic_graph import build_comic_graph
from app.graphs.trace_collector import invoke_with_trace

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FIXED_SCRIPT_DATA = {
    "slang": "Break a leg",
    "origin": "Western theater tradition",
    "explanation": "Used to wish someone good luck, especially before a performance",
    "panel_count": 4,
    "panels": [
        {
            "scene": "A nervous young actor paces backstage, clutching a crumpled script. Stage lights glow in the background.",
            "dialogue": "Narrator: 'Opening night jitters hit hard.'",
        },
        {
            "scene": "Friends gather around the actor, giving thumbs up with warm encouraging smiles.",
            "dialogue": "Friend: 'Hey, break a leg out there!'",
        },
        {
            "scene": "The actor steps onto a bright spotlight stage, audience silhouettes visible in the dark theater.",
            "dialogue": "",
        },
        {
            "scene": "Standing ovation! Confetti falls as the actor beams with joy, taking a bow.",
            "dialogue": "Narrator: 'Break a leg indeed!'",
        },
    ],
}

PROVIDERS = [
    ("dashscope", "qwen"),
    ("openrouter", "gemini"),
    ("openai", "openai"),
]


def load_image_as_base64(image_path: str) -> str:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"测试照片不存在: {image_path}")
    with open(path, "rb") as f:
        raw = f.read()
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else f"image/{suffix.lstrip('.')}"
    b64 = base64.b64encode(raw).decode("ascii")
    logger.info("加载测试照片: %s (%d bytes)", path.name, len(raw))
    return f"data:{mime};base64,{b64}"


def save_result_image(base64_data: str, output_path: Path) -> int:
    if "," in base64_data:
        b64 = base64_data.split(",", 1)[1]
    else:
        b64 = base64_data
    raw = base64.b64decode(b64)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    logger.info("保存结果: %s (%d bytes)", output_path.name, len(raw))
    return len(raw)


async def run_pipeline_for_provider(
    provider_name: str,
    label: str,
    reference_image: str,
    output_dir: Path,
) -> dict:
    import os
    os.environ["IMAGE_GEN_PROVIDER"] = provider_name
    get_cached_settings.cache_clear()
    settings = Settings()

    graph = build_comic_graph()
    inputs = {
        **FIXED_SCRIPT_DATA,
        "reference_image": reference_image,
    }

    logger.info("=" * 60)
    logger.info("开始测试: %s (%s)", label, provider_name)
    logger.info("=" * 60)

    t0 = time.monotonic()
    try:
        result, trace_id = await invoke_with_trace(
            graph, inputs, settings,
            flow_type="comic", request_id=f"comparison-{label}",
        )
        elapsed = time.monotonic() - t0

        image_base64 = result.get("image_base64", "")
        if not image_base64:
            return {
                "provider": label, "status": "FAIL",
                "error": "pipeline 未返回 image_base64",
                "elapsed_s": round(elapsed, 2), "file_size": 0,
            }

        output_path = output_dir / f"{label}_result.png"
        file_size = save_result_image(image_base64, output_path)
        return {
            "provider": label, "status": "OK",
            "elapsed_s": round(elapsed, 2), "file_size": file_size,
            "output": str(output_path), "trace_id": trace_id,
        }
    except Exception as exc:
        elapsed = time.monotonic() - t0
        logger.error("%s 失败: %s", label, exc)
        return {
            "provider": label, "status": "FAIL",
            "error": str(exc), "elapsed_s": round(elapsed, 2), "file_size": 0,
        }


async def main():
    parser = argparse.ArgumentParser(description="图生图三模型对比测试")
    parser.add_argument("--image", required=True, help="测试照片路径")
    parser.add_argument("--output", default=str(Path(__file__).parent / "output"), help="输出目录")
    parser.add_argument("--providers", nargs="+", default=None, help="指定 provider")
    args = parser.parse_args()

    reference_image = load_image_as_base64(args.image)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    providers = PROVIDERS
    if args.providers:
        providers = [(p, p) for p in args.providers]

    results = []
    for provider_name, label in providers:
        result = await run_pipeline_for_provider(provider_name, label, reference_image, output_dir)
        results.append(result)

    print("\n" + "=" * 70)
    print("对比结果")
    print("=" * 70)
    print(f"{'Provider':<12} {'Status':<8} {'Time(s)':<10} {'Size(KB)':<12} {'Output'}")
    print("-" * 70)
    for r in results:
        size_kb = round(r["file_size"] / 1024, 1) if r["file_size"] else 0
        output = r.get("output", r.get("error", ""))
        print(f"{r['provider']:<12} {r['status']:<8} {r['elapsed_s']:<10} {size_kb:<12} {output}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
