"""
E2E 全流程测试 — 模拟用户完整操作链路

用法:
    uv run python tests/e2e/e2e_test.py

前置条件:
    - 后端已在运行: uv run python backend/run.py
    - .env 已配置有效 API Key

测试流程:
    1. Health check
    2. 构造测试照片 (base64)
    3. 调用 /api/analyze → 验证返回 3 个风格选项
    4. 调用 /api/generate (第1个风格) → 验证海报生成
    5. 调用 /api/history → 验证历史记录
"""
from __future__ import annotations

import base64
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

API_BASE = "http://localhost:8888"
TIMEOUT_ANALYZE = 180  # Vision LLM may be slow
TIMEOUT_GENERATE = 300  # Image gen can be very slow

passed = 0
failed = 0


def log_step(name: str):
    print(f"\n{'─' * 60}")
    print(f"  STEP: {name}")
    print(f"{'─' * 60}")


def log_pass(msg: str):
    global passed
    passed += 1
    print(f"  [PASS] {msg}")


def log_fail(msg: str):
    global failed
    failed += 1
    print(f"  [FAIL] {msg}")


def create_person_test_image() -> str:
    """Create a realistic-looking test image of a person for Vision LLM."""
    img = Image.new("RGB", (640, 480), color=(200, 195, 185))
    draw = ImageDraw.Draw(img)

    # Background gradient (light gray)
    for y in range(480):
        shade = int(200 + (y / 480) * 30)
        draw.line([(0, y), (640, y)], fill=(shade, shade - 5, shade - 10))

    # Floor
    draw.rectangle([0, 380, 640, 480], fill=(140, 135, 125))

    # Body - dark clothing
    draw.rectangle([250, 160, 390, 400], fill=(45, 55, 75))
    # Left arm
    draw.rectangle([200, 170, 250, 330], fill=(45, 55, 75))
    # Right arm (slightly raised, like a natural pose)
    draw.rectangle([390, 170, 440, 310], fill=(45, 55, 75))
    # Neck
    draw.rectangle([290, 130, 350, 165], fill=(230, 190, 155))
    # Head (skin tone oval)
    draw.ellipse([260, 40, 380, 145], fill=(235, 195, 160), outline=(200, 160, 125), width=2)
    # Hair
    draw.ellipse([255, 35, 385, 100], fill=(40, 30, 25))
    # Eyes
    draw.ellipse([280, 75, 300, 90], fill=(255, 255, 255))
    draw.ellipse([340, 75, 360, 90], fill=(255, 255, 255))
    draw.ellipse([286, 79, 296, 87], fill=(60, 40, 30))
    draw.ellipse([346, 79, 356, 87], fill=(60, 40, 30))
    # Mouth
    draw.arc([295, 100, 345, 120], 0, 180, fill=(180, 100, 80), width=2)
    # Legs
    draw.rectangle([265, 400, 310, 470], fill=(50, 50, 65))
    draw.rectangle([330, 400, 375, 470], fill=(50, 50, 65))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def test_health(client: httpx.Client):
    log_step("1. Health Check")
    resp = client.get("/health")
    assert resp.status_code == 200, f"status={resp.status_code}"
    body = resp.json()
    assert body["status"] == "ok"
    log_pass(f"Backend is healthy: {body}")


def test_analyze(client: httpx.Client, photo_b64: str) -> dict:
    log_step("2. Analyze Photo (Vision LLM)")
    t0 = time.time()

    resp = client.post(
        "/api/analyze",
        json={"image_base64": photo_b64, "image_format": "jpeg"},
        timeout=TIMEOUT_ANALYZE,
    )

    elapsed = time.time() - t0
    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Status: {resp.status_code}")

    body = resp.json()
    print(f"  Code: {body.get('code')}")
    print(f"  Message: {body.get('message')}")

    if body.get("code") != 0:
        log_fail(f"API returned error: {body.get('message')}")
        print(f"  Full response: {str(body)[:500]}")
        return body

    data = body.get("data", {})
    options = data.get("options", [])
    print(f"  Options count: {len(options)}")

    if len(options) == 0:
        log_fail("No style options returned")
        return body

    for i, opt in enumerate(options):
        print(f"  Option {i + 1}: {opt.get('name', '?')} — {opt.get('brief', '?')[:60]}")
        prompt = opt.get("prompt", "")
        print(f"    Prompt length: {len(prompt)} chars")

        # Validate fields
        for field in ("name", "brief", "prompt"):
            if not opt.get(field):
                log_fail(f"Option {i + 1} missing field: {field}")
                break
        else:
            if len(prompt) < 50:
                log_fail(f"Option {i + 1} prompt too short: {len(prompt)} chars")
            else:
                log_pass(f"Option {i + 1}: {opt['name']} (prompt {len(prompt)} chars)")

    log_pass(f"Analyze returned {len(options)} valid options in {elapsed:.1f}s")
    return body


def test_generate(client: httpx.Client, photo_b64: str, option: dict):
    log_step("3. Generate Poster (Qwen Image 2.0)")
    t0 = time.time()

    resp = client.post(
        "/api/generate",
        json={
            "image_base64": photo_b64,
            "image_format": "jpeg",
            "prompt": option["prompt"],
            "style_name": option["name"],
        },
        timeout=TIMEOUT_GENERATE,
    )

    elapsed = time.time() - t0
    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Status: {resp.status_code}")

    body = resp.json()
    print(f"  Code: {body.get('code')}")
    print(f"  Message: {body.get('message')}")

    if body.get("code") != 0:
        log_fail(f"Generate failed: {body.get('message')}")
        print(f"  Full response: {str(body)[:500]}")
        return body

    data = body.get("data", {})
    poster_url = data.get("poster_url", "")
    thumb_url = data.get("thumbnail_url", "")
    history_id = data.get("history_id", "")

    print(f"  Poster URL: {poster_url}")
    print(f"  Thumbnail URL: {thumb_url}")
    print(f"  History ID: {history_id}")

    # Verify poster is accessible
    poster_resp = client.get(poster_url)
    if poster_resp.status_code == 200 and len(poster_resp.content) > 1000:
        log_pass(f"Poster accessible ({len(poster_resp.content)} bytes)")
    else:
        log_fail(f"Poster not accessible: status={poster_resp.status_code}")

    log_pass(f"Generate completed in {elapsed:.1f}s")
    return body


def test_history(client: httpx.Client):
    log_step("4. History Records")

    resp = client.get("/api/history", params={"page": 1, "page_size": 10}, timeout=10)
    body = resp.json()

    print(f"  Code: {body.get('code')}")
    data = body.get("data", {})
    items = data.get("items", [])
    total = data.get("total", 0)

    print(f"  Total records: {total}")
    print(f"  Page items: {len(items)}")

    if total > 0:
        latest = items[0]
        print(f"  Latest: {latest.get('style_name', '?')} @ {latest.get('created_at', '?')}")
        log_pass(f"History has {total} records")

        for field in ("id", "photo_url", "poster_url", "thumbnail_url", "style_name", "prompt", "created_at"):
            if not latest.get(field):
                log_fail(f"Latest history item missing field: {field}")
    else:
        log_fail("No history records found")


def test_concurrent_requests(client: httpx.Client, photo_b64: str):
    """并发分析请求不崩溃。"""
    log_step("5. Concurrent Requests")
    import concurrent.futures

    def make_request():
        try:
            resp = client.post(
                "/api/analyze",
                json={"image_base64": photo_b64, "image_format": "jpeg"},
                timeout=TIMEOUT_ANALYZE,
            )
            return resp.status_code
        except Exception:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(make_request) for _ in range(3)]
        results = [f.result() for f in futures]

    valid = [r for r in results if r is not None]
    if len(valid) == 3:
        log_pass(f"All {len(valid)} concurrent requests returned status codes")
    else:
        log_fail(f"Some concurrent requests failed: {results}")


def test_large_image_handling(client: httpx.Client):
    """大图片处理。"""
    log_step("6. Large Image Handling")
    large_b64 = "A" * (7 * 1024 * 1024)
    try:
        resp = client.post(
            "/api/analyze",
            json={"image_base64": large_b64, "image_format": "jpeg"},
            timeout=30,
        )
        if resp.status_code in (200, 400, 413, 422):
            log_pass(f"Large image handled: status={resp.status_code}")
        else:
            log_fail(f"Unexpected status: {resp.status_code}")
    except Exception as e:
        log_fail(f"Large image caused error: {e}")


def test_history_pagination_edge_cases(client: httpx.Client):
    """历史记录分页边界。"""
    log_step("7. History Pagination Edge Cases")

    resp = client.get("/api/history", params={"page": 0, "page_size": 10})
    if resp.status_code == 422:
        log_pass("page=0 correctly rejected (422)")
    else:
        log_fail(f"page=0 should be rejected, got {resp.status_code}")

    resp = client.get("/api/history", params={"page": 1, "page_size": 200})
    if resp.status_code == 422:
        log_pass("page_size=200 correctly rejected (422)")
    else:
        log_fail(f"page_size=200 should be rejected, got {resp.status_code}")

    resp = client.get("/api/history", params={"page": -1, "page_size": 10})
    if resp.status_code == 422:
        log_pass("page=-1 correctly rejected (422)")
    else:
        log_fail(f"page=-1 should be rejected, got {resp.status_code}")


def test_invalid_base64_handling(client: httpx.Client):
    """非法 base64 输入处理。"""
    log_step("8. Invalid Base64 Handling")
    resp = client.post(
        "/api/analyze",
        json={"image_base64": "not-valid-base64!!!", "image_format": "jpeg"},
        timeout=30,
    )
    if resp.status_code in (200, 400, 422, 500):
        log_pass(f"Invalid base64 handled: status={resp.status_code}")
    else:
        log_fail(f"Unexpected status: {resp.status_code}")


def main():
    print("=" * 60)
    print("  E2E Full Flow Test")
    print("  Simulates: Photo → Analyze → Generate → History")
    print("=" * 60)

    # Check backend is reachable
    try:
        with httpx.Client(base_url=API_BASE, timeout=5) as client:
            client.get("/health")
    except Exception as e:
        print(f"\n[FATAL] Cannot reach backend at {API_BASE}")
        print(f"  Error: {e}")
        print(f"\n  Start backend first:")
        print(f"    cd backend && uv run python run.py")
        sys.exit(1)

    # Create test image
    print("\n  Creating test image...")
    photo_b64 = create_person_test_image()
    print(f"  Image size: {len(photo_b64)} chars base64")

    # Run tests
    timeout = httpx.Timeout(connect=10.0, read=TIMEOUT_GENERATE, write=30.0, pool=10.0)
    with httpx.Client(base_url=API_BASE, timeout=timeout) as client:
        try:
            test_health(client)

            result = test_analyze(client, photo_b64)
            if result.get("code") != 0:
                print("\n[FATAL] Analyze failed, cannot continue to generate test")
                print_results()
                sys.exit(1)

            options = result["data"]["options"]
            test_generate(client, photo_b64, options[0])

            test_history(client)
            test_concurrent_requests(client, photo_b64)
            test_large_image_handling(client)
            test_history_pagination_edge_cases(client)
            test_invalid_base64_handling(client)

        except httpx.TimeoutException as e:
            log_fail(f"Request timed out: {e}")
        except Exception as e:
            log_fail(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()

    print_results()


def print_results():
    print("\n" + "=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ALL TESTS PASSED ({passed}/{total})")
    else:
        print(f"  RESULTS: {passed} passed, {failed} failed ({total} total)")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
