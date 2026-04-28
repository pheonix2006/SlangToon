"""LLM Benchmark — GLM-4.6V vs Qwen 3.6 Plus, real script prompt."""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

# load .env from project root
from dotenv import load_dotenv
import os
load_dotenv(ROOT / ".env")

from app.prompts.script_prompt import build_system_prompt
from app.slang_blacklist import SlangBlacklist

BLACKLIST_FILE = str(ROOT / "data" / "slang_blacklist.json")
blacklist = SlangBlacklist(file_path=BLACKLIST_FILE)
recent = blacklist.get_recent(50)
SYSTEM_PROMPT = build_system_prompt(recent)
USER_MSG = "Generate a random classical idiom and its modern comic script. JSON only."

MODELS = [
    {
        "name": "GLM-4.6V",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": os.getenv("OPENAI_MODEL", "glm-4.6v"),
    },
    {
        "name": "GLM-5V-Turbo",
        "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "glm-5v-turbo",
    },
    {
        "name": "Qwen 3.6 Plus (OpenRouter)",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_IMAGE_APIKEY", ""),
        "model": "qwen/qwen3.6-plus",
    },
]


async def stream_call(cfg: dict) -> dict:
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_MSG},
        ],
        "max_tokens": 16384,
        "temperature": 0.9,
        "stream": True,
    }

    thinking_parts, content_parts = [], []
    first_any_token = first_thinking = first_content = None
    thinking_chunks = content_chunks = 0
    usage = {}

    async with httpx.AsyncClient(timeout=300.0) as client:
        t0 = time.perf_counter()
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                return {"error": f"{resp.status_code}: {body.decode()[:300]}"}

            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                if raw.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {})
                now = time.perf_counter()

                reasoning = delta.get("reasoning_content") or delta.get("reasoning") or ""
                if reasoning:
                    if first_any_token is None:
                        first_any_token = now
                    if first_thinking is None:
                        first_thinking = now
                    thinking_parts.append(reasoning)
                    thinking_chunks += 1

                ct = delta.get("content") or ""
                if ct:
                    if first_any_token is None:
                        first_any_token = now
                    if first_content is None:
                        first_content = now
                    content_parts.append(ct)
                    content_chunks += 1

                if "usage" in chunk:
                    usage = chunk["usage"]

        t_end = time.perf_counter()

    content_text = "".join(content_parts)
    thinking_text = "".join(thinking_parts)
    total = t_end - t0

    r = {
        "name": cfg["name"],
        "model": cfg["model"],
        "total_time": total,
        "ttft_any": (first_any_token - t0) if first_any_token else None,
        "thinking_text": thinking_text,
        "thinking_chunks": thinking_chunks,
        "content_text": content_text,
        "content_chunks": content_chunks,
        "usage": usage,
    }

    if first_thinking and first_content:
        r["thinking_duration"] = first_content - first_thinking
        r["thinking_speed"] = thinking_chunks / (first_content - first_thinking) if (first_content - first_thinking) > 0 else 0
    if first_content:
        gen = t_end - first_content
        r["content_gen_time"] = gen
        r["content_speed_chunks"] = content_chunks / gen if gen > 0 else 0
        r["ttft_content"] = first_content - t0
    elif first_any_token:
        gen = t_end - first_any_token
        r["content_gen_time"] = gen
        r["content_speed_chunks"] = content_chunks / gen if gen > 0 else 0
        r["ttft_content"] = first_any_token - t0

    return r


def validate_script(text: str) -> dict:
    """Validate JSON output against script schema."""
    try:
        text = text.strip()
        import re
        md = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if md:
            text = md.group(1).strip()
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
        data = json.loads(text)
    except Exception as e:
        return {"valid": False, "reason": f"JSON parse failed: {e}"}

    errors = []
    for f in ("slang", "origin", "explanation", "panel_count", "panels"):
        if f not in data:
            errors.append(f"missing field: {f}")
    if "panel_count" in data and data["panel_count"] != 4:
        errors.append(f"panel_count={data['panel_count']}, expected 4")
    if "panels" in data and "panel_count" in data:
        if len(data["panels"]) != data.get("panel_count", 0):
            errors.append(f"panels len={len(data['panels'])} != panel_count={data['panel_count']}")
    if "panels" in data:
        for i, p in enumerate(data["panels"]):
            if "scene" not in p:
                errors.append(f"panel[{i}] missing scene")
            if "dialogue" not in p:
                errors.append(f"panel[{i}] missing dialogue")

    return {"valid": len(errors) == 0, "errors": errors, "data": data}


def print_result(r: dict):
    if "error" in r:
        print(f"\n{'='*60}")
        print(f"  {r.get('name', '?')} — ERROR: {r['error']}")
        print(f"{'='*60}")
        return

    print(f"\n{'='*60}")
    print(f"  {r['name']}  ({r['model']})")
    print(f"{'='*60}")

    print(f"\n  [Timing]")
    print(f"  First token (any):     {r['ttft_any']:.2f}s" if r.get('ttft_any') is not None else "  First token: N/A")
    if r.get("thinking_duration"):
        print(f"  Thinking duration:     {r['thinking_duration']:.2f}s  ({r['thinking_chunks']} chunks, {r.get('thinking_speed',0):.1f} c/s)")
    if r.get("ttft_content") is not None:
        print(f"  First content token:   {r['ttft_content']:.2f}s")
    if r.get("content_gen_time"):
        print(f"  Content generation:    {r['content_gen_time']:.2f}s  ({r['content_chunks']} chunks, {r.get('content_speed_chunks',0):.1f} c/s)")
    print(f"  Total time:            {r['total_time']:.2f}s")

    u = r.get("usage", {})
    if u:
        pt = u.get("prompt_tokens", 0)
        ct = u.get("completion_tokens", 0)
        print(f"\n  [Tokens]")
        print(f"  Prompt:       {pt}")
        print(f"  Completion:   {ct}")
        if r.get("content_gen_time") and r["content_gen_time"] > 0:
            # estimate content-only tokens by ratio
            total_chars = len(r.get("thinking_text", "")) + len(r.get("content_text", ""))
            if total_chars > 0:
                content_ratio = len(r["content_text"]) / total_chars
                est_content_tokens = int(ct * content_ratio)
                est_thinking_tokens = ct - est_content_tokens
                print(f"  Est. thinking tokens:  ~{est_thinking_tokens}")
                print(f"  Est. content tokens:   ~{est_content_tokens}")
                if r["content_gen_time"] > 0:
                    print(f"  Content token speed:   ~{est_content_tokens / r['content_gen_time']:.1f} tokens/s")

    v = validate_script(r["content_text"])
    print(f"\n  [Quality]")
    print(f"  JSON valid:   {'YES' if v['valid'] else 'NO'}")
    if not v["valid"]:
        for e in v.get("errors", []):
            print(f"    - {e}")
        if "reason" in v:
            print(f"    - {v['reason']}")

    if v.get("data"):
        d = v["data"]
        print(f"  Slang:        {d.get('slang', 'N/A')}")
        print(f"  Origin:       {d.get('origin', 'N/A')}")
        exp = d.get("explanation", "")
        print(f"  Explanation:  {exp[:120]}{'...' if len(exp)>120 else ''}")
        panels = d.get("panels", [])
        print(f"  Panels:       {len(panels)}")
        for i, p in enumerate(panels):
            scene = p.get("scene", "")
            dial = p.get("dialogue", "")
            print(f"    [{i+1}] scene:    {scene[:80]}{'...' if len(scene)>80 else ''}")
            print(f"        dialogue: {dial[:60]}{'...' if len(dial)>60 else ''}")

    if r.get("thinking_text"):
        t = r["thinking_text"]
        print(f"\n  [Thinking preview — {len(t)} chars]")
        print(f"  {t[:200]}{'...' if len(t)>200 else ''}")


async def main():
    print("=" * 60)
    print("  LLM Benchmark — Real Script Prompt")
    print(f"  Blacklist size: {len(recent)}")
    print(f"  System prompt length: {len(SYSTEM_PROMPT)} chars")
    print("=" * 60)

    results = []
    for cfg in MODELS:
        print(f"\nTesting {cfg['name']}...")
        r = await stream_call(cfg)
        results.append(r)
        print_result(r)

    def fmt(r, key, suffix="s", precision=2):
        v = r.get(key)
        if v is None:
            return "N/A"
        return f"{v:.{precision}f}{suffix}"

    # Summary table
    print(f"\n\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")

    valid_results = [r for r in results if "error" not in r]
    if not valid_results:
        print("  No valid results.")
        return

    # dynamic columns
    col_w = 18
    name_col = 28
    header = f"{'Metric':<{name_col}}"
    for r in valid_results:
        header += f" | {r['name']:>{col_w}}"
    print(header)
    print("-" * len(header))

    rows = [
        ("First token (any)", "ttft_any", "s"),
        ("Thinking duration", "thinking_duration", "s"),
        ("First content token", "ttft_content", "s"),
        ("Content gen time", "content_gen_time", "s"),
        ("Total time", "total_time", "s"),
        ("Content chunks/s", "content_speed_chunks", ""),
    ]
    for label, key, suf in rows:
        line = f"  {label:<{name_col - 2}}"
        for r in valid_results:
            line += f" | {fmt(r, key, suf):>{col_w}}"
        print(line)

    line = f"  {'JSON valid':<{name_col - 2}}"
    for r in valid_results:
        v = validate_script(r.get("content_text", ""))["valid"]
        line += f" | {'YES' if v else 'NO':>{col_w}}"
    print(line)


if __name__ == "__main__":
    asyncio.run(main())
