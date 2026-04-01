"""
E2E 全流程测试 — 模拟用户完整操作链路 (SlangToon)

用法:
    uv run python tests/e2e/e2e_test.py

前置条件:
    - 后端已在运行: uv run python backend/run.py
    - .env 已配置有效 API Key

测试流程:
    1. Health check
    2. 调用 /api/generate-script → 验证返回俚语 + 漫画脚本
    3. 调用 /api/generate-comic (用脚本数据) → 验证漫画生成
    4. 调用 /api/history → 验证历史记录
"""
from __future__ import annotations

import sys
import time

import httpx

API_BASE = "http://localhost:8888"
TIMEOUT_SCRIPT = 180  # LLM script generation may be slow
TIMEOUT_COMIC = 300   # Image gen can be very slow

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


def test_health(client: httpx.Client):
    log_step("1. Health Check")
    resp = client.get("/health")
    assert resp.status_code == 200, f"status={resp.status_code}"
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "SlangToon"
    log_pass(f"Backend is healthy: {body}")


def test_generate_script(client: httpx.Client) -> dict:
    log_step("2. Generate Script (GLM-4.6V LLM)")
    t0 = time.time()

    resp = client.post(
        "/api/generate-script",
        json={},
        timeout=TIMEOUT_SCRIPT,
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
    slang = data.get("slang", "")
    origin = data.get("origin", "")
    explanation = data.get("explanation", "")
    panel_count = data.get("panel_count", 0)
    panels = data.get("panels", [])

    print(f"  Slang: {slang}")
    print(f"  Origin: {origin}")
    print(f"  Explanation: {explanation[:80]}")
    print(f"  Panel count: {panel_count}")

    # Validate required fields
    for field in ("slang", "origin", "explanation", "panel_count", "panels"):
        if not data.get(field):
            log_fail(f"Missing field: {field}")

    if not isinstance(panel_count, int) or not (4 <= panel_count <= 6):
        log_fail(f"panel_count out of range [4,6]: {panel_count}")
    else:
        log_pass(f"panel_count valid: {panel_count}")

    if len(panels) != panel_count:
        log_fail(f"panels count ({len(panels)}) != panel_count ({panel_count})")
    else:
        log_pass(f"panels count matches panel_count: {len(panels)}")

    for i, panel in enumerate(panels):
        scene = panel.get("scene", "")
        dialogue = panel.get("dialogue", "")
        print(f"  Panel {i + 1}: scene={scene[:50]}... dialogue={dialogue[:40]}...")
        if not scene:
            log_fail(f"Panel {i + 1} missing scene")
        else:
            log_pass(f"Panel {i + 1}: scene OK ({len(scene)} chars)")

    log_pass(f"Script generated in {elapsed:.1f}s: '{slang}' with {panel_count} panels")
    return body


def test_generate_comic(client: httpx.Client, script_data: dict) -> dict:
    log_step("3. Generate Comic (Qwen Image 2.0)")
    t0 = time.time()

    resp = client.post(
        "/api/generate-comic",
        json=script_data,
        timeout=TIMEOUT_COMIC,
    )

    elapsed = time.time() - t0
    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Status: {resp.status_code}")

    body = resp.json()
    print(f"  Code: {body.get('code')}")
    print(f"  Message: {body.get('message')}")

    if body.get("code") != 0:
        log_fail(f"Generate comic failed: {body.get('message')}")
        print(f"  Full response: {str(body)[:500]}")
        return body

    data = body.get("data", {})
    comic_url = data.get("comic_url", "")
    thumbnail_url = data.get("thumbnail_url", "")
    history_id = data.get("history_id", "")

    print(f"  Comic URL: {comic_url}")
    print(f"  Thumbnail URL: {thumbnail_url}")
    print(f"  History ID: {history_id}")

    # Validate required fields
    for field in ("comic_url", "thumbnail_url", "history_id"):
        if not data.get(field):
            log_fail(f"Missing field: {field}")

    # Verify comic image is accessible
    comic_resp = client.get(comic_url)
    if comic_resp.status_code == 200 and len(comic_resp.content) > 1000:
        log_pass(f"Comic image accessible ({len(comic_resp.content)} bytes)")
    else:
        log_fail(f"Comic image not accessible: status={comic_resp.status_code}")

    log_pass(f"Comic generated in {elapsed:.1f}s")
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
        print(f"  Latest: {latest.get('slang', '?')} @ {latest.get('created_at', '?')}")
        log_pass(f"History has {total} records")

        for field in ("id", "slang", "origin", "explanation", "panel_count",
                       "comic_url", "thumbnail_url", "comic_prompt", "created_at"):
            if not latest.get(field):
                log_fail(f"Latest history item missing field: {field}")
    else:
        log_fail("No history records found")


def test_concurrent_script_requests(client: httpx.Client):
    """并发脚本生成请求不崩溃。"""
    log_step("5. Concurrent Script Requests")
    import concurrent.futures

    def make_request():
        try:
            resp = client.post(
                "/api/generate-script",
                json={},
                timeout=TIMEOUT_SCRIPT,
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


def test_history_pagination_edge_cases(client: httpx.Client):
    """历史记录分页边界。"""
    log_step("6. History Pagination Edge Cases")

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


def test_generate_comic_validation_errors(client: httpx.Client):
    """漫画生成请求验证错误。"""
    log_step("7. Comic Generation Validation Errors")

    # Missing required fields
    resp = client.post(
        "/api/generate-comic",
        json={"slang": "test"},
        timeout=10,
    )
    if resp.status_code == 422:
        log_pass("Missing required fields correctly rejected (422)")
    else:
        log_fail(f"Missing fields should be rejected, got {resp.status_code}")

    # Empty request body
    resp = client.post(
        "/api/generate-comic",
        json={},
        timeout=10,
    )
    if resp.status_code == 422:
        log_pass("Empty request body correctly rejected (422)")
    else:
        log_fail(f"Empty body should be rejected, got {resp.status_code}")

    # panel_count out of range
    resp = client.post(
        "/api/generate-comic",
        json={
            "slang": "test",
            "origin": "test",
            "explanation": "test",
            "panel_count": 10,
            "panels": [{"scene": "test", "dialogue": ""}],
        },
        timeout=10,
    )
    if resp.status_code == 422:
        log_pass("panel_count=10 correctly rejected (422)")
    else:
        log_fail(f"panel_count=10 should be rejected, got {resp.status_code}")


def test_health_app_name(client: httpx.Client):
    """验证 health 端点返回正确的应用名称。"""
    log_step("8. Health App Name Validation")
    resp = client.get("/health")
    body = resp.json()
    app_name = body.get("app", "")
    if app_name == "SlangToon":
        log_pass(f"App name correct: {app_name}")
    else:
        log_fail(f"App name incorrect: expected 'SlangToon', got '{app_name}'")


def main():
    print("=" * 60)
    print("  SlangToon E2E Full Flow Test")
    print("  Simulates: Script Generation → Comic Generation → History")
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

    # Run tests
    timeout = httpx.Timeout(connect=10.0, read=TIMEOUT_COMIC, write=30.0, pool=10.0)
    with httpx.Client(base_url=API_BASE, timeout=timeout) as client:
        try:
            test_health(client)
            test_health_app_name(client)

            result = test_generate_script(client)
            if result.get("code") != 0:
                print("\n[FATAL] Script generation failed, cannot continue to comic test")
                print_results()
                sys.exit(1)

            script_data = result["data"]
            # Extract script data fields for comic generation request
            comic_request_data = {
                "slang": script_data["slang"],
                "origin": script_data["origin"],
                "explanation": script_data["explanation"],
                "panel_count": script_data["panel_count"],
                "panels": script_data["panels"],
            }
            test_generate_comic(client, comic_request_data)

            test_history(client)
            test_concurrent_script_requests(client)
            test_history_pagination_edge_cases(client)
            test_generate_comic_validation_errors(client)

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
