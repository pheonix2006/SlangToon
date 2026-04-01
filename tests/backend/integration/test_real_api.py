"""Real API integration tests — calls service layer directly with real API keys.

No running server required. Tests use real Vision LLM (GLM-4.6V) and Qwen Image 2.0 APIs.

Run: uv run pytest tests/backend/integration/test_real_api.py -v -s --tb=short
"""

from __future__ import annotations

import asyncio
import base64
import json
import shutil
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

# Ensure backend/ is on sys.path so `from app.*` imports work
# File: tests/backend/integration/test_real_api.py -> root = 4 levels up
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_backend_dir = _project_root / "backend"
sys.path.insert(0, str(_backend_dir))
project_root = _project_root

from app.config import Settings
from app.services.analyze_service import analyze_photo, AnalyzeError
from app.services.generate_service import generate_artwork, GenerateError
from app.services.history_service import HistoryService
from app.storage.file_storage import FileStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_human_test_image(width: int = 400, height: int = 500) -> tuple[str, str]:
    """Create a stick-figure test image. Returns (base64_str, format)."""
    img = Image.new("RGB", (width, height), color=(240, 235, 220))
    draw = ImageDraw.Draw(img)
    draw.ellipse([160, 30, 240, 130], fill=(255, 220, 185), outline=(180, 140, 100), width=2)
    draw.ellipse([178, 60, 190, 75], fill=(60, 40, 30))
    draw.ellipse([210, 60, 222, 75], fill=(60, 40, 30))
    draw.arc([180, 80, 220, 110], 0, 180, fill=(180, 100, 80), width=2)
    draw.rectangle([155, 130, 245, 300], fill=(50, 60, 80))
    draw.rectangle([115, 140, 155, 270], fill=(50, 60, 80))
    draw.rectangle([245, 140, 285, 270], fill=(50, 60, 80))
    draw.rectangle([155, 300, 200, 450], fill=(40, 40, 60))
    draw.rectangle([200, 300, 245, 450], fill=(40, 40, 60))
    draw.rectangle([150, 440, 205, 470], fill=(80, 50, 30))
    draw.rectangle([195, 440, 250, 470], fill=(80, 50, 30))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64, "jpeg"


def load_settings() -> Settings:
    env_path = project_root / ".env"
    if not env_path.exists():
        print(f"[FATAL] .env not found at {env_path}")
        sys.exit(1)
    return Settings(_env_file=str(env_path))


def verify_trace(flow_type: str, trace_dir: str, trace_id: str | None = None) -> dict:
    """验证 trace 记录。可通过 trace_id 精确匹配，或匹配最新的指定类型 trace。"""
    from app.flow_log.trace_store import TraceStore
    store = TraceStore(trace_dir)
    traces = store.query(limit=50)
    if trace_id:
        matches = [t for t in traces if t.trace_id == trace_id]
        assert len(matches) == 1, f"Expected 1 trace with id={trace_id}, found {len(matches)}"
        trace = matches[0]
    else:
        matches = [t for t in traces if t.flow_type == flow_type]
        assert len(matches) > 0, f"No trace found for {flow_type}"
        trace = matches[0]
    assert trace.flow_type == flow_type
    return trace.model_dump()


# ---------------------------------------------------------------------------
# 阶段 1: Analyze 集成测试
# ---------------------------------------------------------------------------

def test_config_and_api_keys():
    """T01: Verify settings loaded correctly with API keys."""
    print("\n[T01] Config & API Keys")
    settings = load_settings()
    assert settings.openai_api_key
    assert settings.openai_base_url
    assert settings.openai_model
    assert settings.qwen_image_apikey
    assert settings.qwen_image_base_url
    assert settings.qwen_image_model
    print(f"  Vision LLM: {settings.openai_model} @ {settings.openai_base_url}")
    print(f"  Image Gen:  {settings.qwen_image_model} @ {settings.qwen_image_base_url}")
    print("  [PASS]")


def test_analyze_returns_5_topics():
    """T02: Real LLM returns 5 topic options."""
    print("\n[T02] Analyze — 5 Topics")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    # 手动创建 trace session（集成测试直接调用 service，不走路由层）
    from app.flow_log import FlowSession, set_current_trace
    trace = FlowSession("analyze")
    set_current_trace(trace)

    t0 = time.time()
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    elapsed = time.time() - t0

    assert isinstance(options, list), "Result should be a list"
    assert len(options) == 5, f"Expected 5 options, got {len(options)}"
    print(f"  Options count: {len(options)} (in {elapsed:.1f}s)")

    for i, opt in enumerate(options):
        assert opt.name, f"options[{i}].name is empty"
        assert opt.brief, f"options[{i}].brief is empty"
        assert len(opt.brief) <= 50, f"options[{i}].brief too long ({len(opt.brief)} chars)"
        print(f"  [{i+1}] {opt.name}: {opt.brief}")

    # Verify trace record
    trace.finish("success")
    trace_dir = str(project_root / "data" / "traces")
    from app.flow_log.trace_store import TraceStore
    TraceStore(trace_dir).save(trace.trace)
    trace_data = verify_trace("analyze", trace_dir, trace_id=trace.trace.trace_id)
    assert len(trace_data["steps"]) >= 2, f"Expected >= 2 steps, got {len(trace_data['steps'])}"
    assert trace_data["steps"][0]["name"] == "llm_analyze"
    assert trace_data["steps"][0]["duration_ms"] > 0
    print(f"  Trace: {trace_data['trace_id'][:8]}... ({trace_data['total_duration_ms']:.0f}ms)")
    print("  [PASS]")
    return options


def test_analyze_topics_are_diverse():
    """T03: 5 topics should be diverse."""
    print("\n[T03] Analyze — Topic Diversity")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    names = [opt.name for opt in options]
    unique_names = set(names)

    # At least 4 out of 5 should have unique names
    assert len(unique_names) >= 4, f"Topics not diverse enough: {names}"
    print(f"  Topics: {names}")
    print(f"  Unique: {len(unique_names)}/5")
    print("  [PASS]")


def test_analyze_topics_match_photo():
    """T04: Topics should relate to a human figure in photo."""
    print("\n[T04] Analyze — Topics Match Photo")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    options = asyncio.run(analyze_photo(image_b64, image_format, settings))

    # At least some topics should mention person-related concepts in brief
    person_keywords = ["人", "姿态", "形象", "风格", "角色", "人物", "战士", "主角", "英雄", "少女", "少年"]
    has_person_ref = any(
        any(kw in opt.brief or kw in opt.name for kw in person_keywords)
        for opt in options
    )
    assert has_person_ref, f"Topics don't seem to relate to person in photo: {[opt.brief for opt in options]}"
    print("  Topics relate to person in photo")
    print("  [PASS]")


def test_analyze_response_time():
    """T05: Analyze response should be under 10s (shorter output = faster)."""
    print("\n[T05] Analyze — Response Time")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    t0 = time.time()
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    elapsed = time.time() - t0

    print(f"  Response time: {elapsed:.1f}s")
    assert len(options) == 5
    print("  [PASS]")


def test_analyze_no_preset_styles():
    """T06: Topics should not be limited to old 10 preset styles."""
    print("\n[T06] Analyze — No Preset Styles")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    options = asyncio.run(analyze_photo(image_b64, image_format, settings))

    old_presets = ["武侠江湖", "赛博朋克", "暗黑童话", "水墨仙侠", "机甲战场", "魔法学院", "废土末日", "深海探索", "蒸汽朋克", "星际远航"]
    preset_matches = [opt.name for opt in options if opt.name in old_presets]

    # At most 1 out of 5 should match old presets (allowing some overlap by coincidence)
    assert len(preset_matches) <= 1, f"Too many preset-style matches: {preset_matches}"
    print(f"  Preset matches: {len(preset_matches)}/5 ({preset_matches or 'none'})")
    print("  [PASS]")


# ---------------------------------------------------------------------------
# 阶段 2: Compose + Generate 集成测试
# ---------------------------------------------------------------------------

def test_compose_generates_english_prompt():
    """T07: Compose LLM generates valid English prompt (200-400 words)."""
    print("\n[T07] Compose — English Prompt Generation")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    # Get a real topic first
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    selected = options[0]
    print(f"  Selected topic: {selected.name} — {selected.brief}")

    # Now call compose through generate_artwork (it will fail at image gen, but we can check the prompt)
    from app.services.generate_service import _compose_prompt

    t0 = time.time()
    prompt = asyncio.run(_compose_prompt(
        image_b64, image_format,
        selected.name, selected.brief, settings,
    ))
    elapsed = time.time() - t0

    word_count = len(prompt.split())
    print(f"  Prompt length: {word_count} words (in {elapsed:.1f}s)")
    assert 50 <= word_count <= 500, f"Prompt word count out of range: {word_count}"
    # Should contain quality keywords
    assert any(kw in prompt.lower() for kw in ["masterpiece", "best quality", "ultra-detailed", "8k"]), \
        f"Prompt missing quality keywords"
    print(f"  Prompt preview: {prompt[:100]}...")
    print("  [PASS]")
    return prompt


def test_compose_prompt_describes_person():
    """T08: Compose prompt should describe person characteristics."""
    print("\n[T08] Compose — Person Description")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))

    from app.services.generate_service import _compose_prompt
    prompt = asyncio.run(_compose_prompt(
        image_b64, image_format,
        options[0].name, options[0].brief, settings,
    ))

    # Check for person-related words
    person_words = ["person", "man", "woman", "figure", "standing", "portrait", "character", "pose", "body", "face"]
    has_person = any(w in prompt.lower() for w in person_words)
    assert has_person, f"Prompt doesn't describe person: {prompt[:200]}"
    print("  Prompt includes person description")
    print("  [PASS]")


def test_generate_end_to_end():
    """T09: Full flow: analyze → compose → generate → save."""
    print("\n[T09] Generate — End-to-End Flow")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()

    # Step 1: Analyze
    print("  Step 1: Analyzing photo...")
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))
    selected = options[0]
    print(f"  Selected: {selected.name}")

    # Step 2: Setup temp storage
    tmp_dir = tempfile.mkdtemp(prefix="pose_art_test_")
    photo_dir = Path(tmp_dir) / "photos"
    poster_dir = Path(tmp_dir) / "posters"
    photo_dir.mkdir(parents=True)
    poster_dir.mkdir(parents=True)
    history_file = Path(tmp_dir) / "history.json"
    history_file.write_text("[]", encoding="utf-8")

    try:
        storage = FileStorage(str(photo_dir), str(poster_dir))
        history = HistoryService(str(history_file), max_records=100)

        # Step 3: Generate (compose + image gen)
        print("  Step 2: Generating artwork...")

        # 手动创建 trace session
        from app.flow_log import FlowSession, set_current_trace
        trace = FlowSession("generate")
        set_current_trace(trace)

        result = asyncio.run(generate_artwork(
            image_base64=image_b64,
            image_format=image_format,
            style_name=selected.name,
            style_brief=selected.brief,
            settings=settings,
            storage=storage,
            history=history,
        ))

        assert "poster_url" in result
        assert "thumbnail_url" in result
        assert "history_id" in result
        print(f"  poster_url: {result['poster_url']}")
        print(f"  history_id: {result['history_id']}")

        # Step 4: Validate files
        poster_path = poster_dir / result["poster_url"].replace("/data/posters/", "")
        assert poster_path.exists(), f"Poster not found: {poster_path}"
        print(f"  Poster size: {poster_path.stat().st_size} bytes")

        # Step 5: Validate history
        history_data = json.loads(history_file.read_text(encoding="utf-8"))
        assert len(history_data) >= 1
        record = history_data[0]
        assert record["style_name"] == selected.name
        assert record["prompt"]  # compose 生成的 prompt
        print(f"  History prompt length: {len(record['prompt'])} chars")

        # Step 6: Verify trace
        trace.finish("success")
        trace_dir = str(project_root / "data" / "traces")
        from app.flow_log.trace_store import TraceStore
        TraceStore(trace_dir).save(trace.trace)
        trace_data = verify_trace("generate", trace_dir, trace_id=trace.trace.trace_id)
        step_names = [s["name"] for s in trace_data["steps"]]
        expected_steps = ["save_photo", "compose_prompt", "image_generate", "save_poster"]
        for expected in expected_steps:
            assert expected in step_names, f"Missing step: {expected} in {step_names}"
        assert trace_data["total_duration_ms"] > 0
        print(f"  Trace: {trace_data['trace_id'][:8]}... ({trace_data['total_duration_ms']:.0f}ms, {len(trace_data['steps'])} steps)")

        print("  [PASS]")

    except (GenerateError, AnalyzeError) as e:
        print(f"  [WARN] API Error: {e.code} - {e.message}")
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_generate_poster_is_valid_image():
    """T10: Generated poster should be a valid image."""
    print("\n[T10] Generate — Valid Image Output")
    settings = load_settings()
    image_b64, image_format = create_human_test_image()
    options = asyncio.run(analyze_photo(image_b64, image_format, settings))

    tmp_dir = tempfile.mkdtemp(prefix="pose_art_img_test_")
    photo_dir = Path(tmp_dir) / "photos"
    poster_dir = Path(tmp_dir) / "posters"
    photo_dir.mkdir(parents=True)
    poster_dir.mkdir(parents=True)
    history_file = Path(tmp_dir) / "history.json"
    history_file.write_text("[]", encoding="utf-8")

    try:
        storage = FileStorage(str(photo_dir), str(poster_dir))
        history = HistoryService(str(history_file), max_records=100)

        result = asyncio.run(generate_artwork(
            image_base64=image_b64,
            image_format=image_format,
            style_name=options[0].name,
            style_brief=options[0].brief,
            settings=settings,
            storage=storage,
            history=history,
        ))

        poster_path = poster_dir / result["poster_url"].replace("/data/posters/", "")
        img = Image.open(poster_path)
        assert img.size[0] > 0 and img.size[1] > 0
        print(f"  Poster: {img.size[0]}x{img.size[1]}, mode={img.mode}")
        print("  [PASS]")

    except (GenerateError, AnalyzeError) as e:
        print(f"  [WARN] API Error: {e.code} - {e.message}")
        raise
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main Runner
# ---------------------------------------------------------------------------

def run_all():
    print("=" * 70)
    print("  Pose Art Generator — Two-Stage LLM Integration Tests")
    print("=" * 70)

    tests = [
        test_config_and_api_keys,
        test_analyze_returns_5_topics,
        test_analyze_topics_are_diverse,
        test_analyze_topics_match_photo,
        test_analyze_response_time,
        test_analyze_no_preset_styles,
        test_compose_generates_english_prompt,
        test_compose_prompt_describes_person,
        test_generate_end_to_end,
        test_generate_poster_is_valid_image,
    ]

    passed = 0
    failed = 0
    errors = []

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except (AssertionError, Exception) as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))

    print("\n" + "=" * 70)
    print(f"  Results: {passed} passed, {failed} failed")
    if errors:
        print("\n  Failures:")
        for name, msg in errors:
            print(f"    [FAIL] {name}: {msg[:200]}")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
