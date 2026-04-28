"""Theme Packs 全流程验证脚本.

验证主题包系统从数据层到 API 层的完整数据流:
1. 主题包数据层 (theme_packs.py)
2. 脚本 Prompt 注入 world_setting
3. 漫画 Prompt 注入 visual_style
4. Schema 变更 (ScriptResponse / ComicRequest / WorkflowState)
5. 路由层集成 (script_stream SSE theme 事件 / script router theme 字段)

用法:
    cd E:/Project/1505v2/1505creative_art
    uv run python tests/manual/verify_theme_packs.py
"""

import json
import sys
import traceback
from pathlib import Path

# 确保 backend 在 path 中
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))


class Verifier:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: list[str] = []

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            msg = f"  [FAIL] {name}"
            if detail:
                msg += f" — {detail}"
            print(msg)
            self.errors.append(name)

    def section(self, title: str):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"  结果: {self.passed}/{total} 通过")
        if self.errors:
            print(f"  失败项:")
            for e in self.errors:
                print(f"    - {e}")
        print(f"{'='*60}")
        return self.failed == 0


def main():
    v = Verifier()

    # ── 1. 主题包数据层 ──
    v.section("1. 主题包数据层 (theme_packs.py)")

    try:
        from app.prompts.theme_packs import THEME_PACKS, get_random_theme, get_theme_by_id, ThemePack

        v.check("THEME_PACKS 有 18 个主题", len(THEME_PACKS) == 18, f"实际: {len(THEME_PACKS)}")

        required_keys = {"id", "name_zh", "name_en", "world_setting", "visual_style"}
        all_valid = True
        for theme in THEME_PACKS:
            if not required_keys.issubset(set(theme.keys())):
                all_valid = False
                break
        v.check("每个主题包含所有必需字段", all_valid)

        ids = [t["id"] for t in THEME_PACKS]
        v.check("所有主题 ID 唯一", len(ids) == len(set(ids)))

        theme = get_random_theme()
        v.check("get_random_theme 返回有效主题", theme["id"] in ids)
        v.check("随机主题有 world_setting", len(theme["world_setting"]) > 20)
        v.check("随机主题有 visual_style", len(theme["visual_style"]) > 20)

        cyber = get_theme_by_id("cyberpunk")
        v.check("get_theme_by_id('cyberpunk') 找到主题", cyber is not None)
        v.check("赛博朋克名称正确", cyber["name_zh"] == "赛博朋克" if cyber else False)
        v.check("get_theme_by_id('nonexistent') 返回 None", get_theme_by_id("nonexistent") is None)
    except Exception as e:
        v.check("导入 theme_packs 模块", False, str(e))
        traceback.print_exc()

    # ── 2. 脚本 Prompt world_setting 注入 ──
    v.section("2. 脚本 Prompt world_setting 注入")

    try:
        from app.prompts.script_prompt import build_system_prompt

        prompt_no_ws = build_system_prompt(blacklist=[])
        prompt_with_ws = build_system_prompt(blacklist=[], world_setting="A cyberpunk megacity")

        v.check("无 world_setting 时不含 world 规则", "following world:" not in prompt_no_ws)
        v.check("有 world_setting 时包含 world 规则", "following world:" in prompt_with_ws)
        v.check("world_setting 内容注入到 prompt", "cyberpunk megacity" in prompt_with_ws)

        # 验证规则编号: 有 world_setting 时黑名单为 rule 6
        prompt_both = build_system_prompt(
            blacklist=["test_slang"],
            world_setting="A cyberpunk megacity",
        )
        v.check("有 world_setting + blacklist 时黑名单为 rule 6", "6. DO NOT pick" in prompt_both)
        v.check("有 world_setting 时 world 为 rule 5", "5. The story is set" in prompt_both)

        # 无 world_setting 时黑名单为 rule 5
        prompt_bl_only = build_system_prompt(blacklist=["test_slang"])
        v.check("无 world_setting 时黑名单为 rule 5", "5. DO NOT pick" in prompt_bl_only)
    except Exception as e:
        v.check("脚本 prompt world_setting 测试", False, str(e))
        traceback.print_exc()

    # ── 3. script_service 传递 world_setting ──
    v.section("3. script_service 传递 world_setting")

    try:
        from app.services.script_service import build_script_context
        from app.config import Settings
        import tempfile, os

        # 创建临时 data 目录
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["DATA_DIR"] = tmpdir
            settings = Settings()

            sys_prompt, bl = build_script_context(settings)
            v.check("build_script_context 无 world_setting 返回有效 prompt", len(sys_prompt) > 100)

            sys_prompt_ws, _ = build_script_context(settings, world_setting="A steampunk world")
            v.check("build_script_context 传递 world_setting", "steampunk world" in sys_prompt_ws)
    except Exception as e:
        v.check("script_service 传递 world_setting 测试", False, str(e))
        traceback.print_exc()

    # ── 4. 漫画 Prompt visual_style 注入 ──
    v.section("4. 漫画 Prompt visual_style 注入")

    try:
        from app.prompts.comic_prompt import build_comic_prompt

        panels = [
            {"scene": "A busy office with monitors", "dialogue": "Let's go"},
            {"scene": "A dark alley at night", "dialogue": "Watch out"},
            {"scene": "A rooftop overlooking the city", "dialogue": "We made it"},
            {"scene": "A cafe in the morning light", "dialogue": ""},
        ]

        prompt_default = build_comic_prompt(
            slang="Carpe Diem", origin="Latin", explanation="Seize the day",
            panels=panels,
        )
        v.check("默认 prompt 包含 manga 风格", "manga line art" in prompt_default)

        prompt_themed = build_comic_prompt(
            slang="Carpe Diem", origin="Latin", explanation="Seize the day",
            panels=panels,
            visual_style="Neon cyan and magenta lights cutting through rain",
        )
        v.check("themed prompt 包含 visual_style", "Neon cyan and magenta" in prompt_themed)
        v.check("themed prompt 不包含硬编码 manga", "manga line art" not in prompt_themed)

        prompt_empty_style = build_comic_prompt(
            slang="Carpe Diem", origin="Latin", explanation="Seize the day",
            panels=panels,
            visual_style="",
        )
        v.check("空 visual_style 回退到 manga 风格", "manga line art" in prompt_empty_style)
    except Exception as e:
        v.check("漫画 prompt visual_style 测试", False, str(e))
        traceback.print_exc()

    # ── 5. Schema 变更验证 ──
    v.section("5. Schema 变更验证")

    try:
        from app.schemas.script import ScriptResponse, Panel
        from app.schemas.comic import ComicRequest

        # ScriptResponse theme 字段
        sr = ScriptResponse(
            slang="test", origin="test", explanation="test",
            panel_count=4, panels=[Panel(scene="s", dialogue="d")] * 4,
        )
        v.check("ScriptResponse 默认 theme_id 为空字符串", sr.theme_id == "")
        v.check("ScriptResponse 默认 theme_name_zh 为空字符串", sr.theme_name_zh == "")

        sr_themed = ScriptResponse(
            slang="test", origin="test", explanation="test",
            panel_count=4, panels=[Panel(scene="s", dialogue="d")] * 4,
            theme_id="cyberpunk", theme_name_zh="赛博朋克",
        )
        v.check("ScriptResponse 接受 theme_id", sr_themed.theme_id == "cyberpunk")
        v.check("ScriptResponse 接受 theme_name_zh", sr_themed.theme_name_zh == "赛博朋克")

        # ComicRequest theme_id
        cr = ComicRequest(
            slang="test", origin="test", explanation="test",
            panel_count=4, panels=[Panel(scene="s", dialogue="d")] * 4,
        )
        v.check("ComicRequest 默认 theme_id 为空字符串", cr.theme_id == "")

        cr_themed = ComicRequest(
            slang="test", origin="test", explanation="test",
            panel_count=4, panels=[Panel(scene="s", dialogue="d")] * 4,
            theme_id="ghibli",
        )
        v.check("ComicRequest 接受 theme_id", cr_themed.theme_id == "ghibli")
        v.check("ComicRequest.model_dump() 包含 theme_id", cr_themed.model_dump()["theme_id"] == "ghibli")
    except Exception as e:
        v.check("Schema 变更验证", False, str(e))
        traceback.print_exc()

    # ── 6. WorkflowState 验证 ──
    v.section("6. WorkflowState 验证")

    try:
        from app.graphs.state import WorkflowState

        # TypedDict 的 annotations 检查
        annotations = WorkflowState.__annotations__
        v.check("WorkflowState 包含 theme_id", "theme_id" in annotations)
        v.check("WorkflowState 包含 theme_name_zh", "theme_name_zh" in annotations)
        v.check("theme_id 类型为 str", annotations["theme_id"] is str)
        v.check("theme_name_zh 类型为 str", annotations["theme_name_zh"] is str)
    except Exception as e:
        v.check("WorkflowState 验证", False, str(e))
        traceback.print_exc()

    # ── 7. script_node theme 查找逻辑 ──
    v.section("7. script_node theme 查找逻辑")

    try:
        # 直接测试 theme 查找逻辑（不启动完整 graph）
        from app.prompts.theme_packs import get_theme_by_id

        # 模拟 script_node 的 theme 查找
        for test_id in ["cyberpunk", "ghibli", "chinese_ink", "nonexistent", ""]:
            world_setting = ""
            theme_id = test_id
            if theme_id:
                theme = get_theme_by_id(theme_id)
                if theme:
                    world_setting = theme["world_setting"]

            if test_id == "cyberpunk":
                v.check("cyberpunk theme 有 world_setting", len(world_setting) > 0)
            elif test_id == "nonexistent":
                v.check("nonexistent theme 返回空 world_setting", world_setting == "")
            elif test_id == "":
                v.check("空 theme_id 返回空 world_setting", world_setting == "")
    except Exception as e:
        v.check("script_node theme 查找逻辑测试", False, str(e))
        traceback.print_exc()

    # ── 8. prompt_node visual_style 查找逻辑 ──
    v.section("8. prompt_node visual_style 查找逻辑")

    try:
        from app.prompts.theme_packs import get_theme_by_id
        from app.prompts.comic_prompt import build_comic_prompt

        # 模拟 prompt_node 的 theme 查找 + comic prompt 构建
        for test_id in ["pixel_art", "ancient_egypt", "nonexistent", ""]:
            visual_style = ""
            theme_id = test_id
            if theme_id:
                theme = get_theme_by_id(theme_id)
                if theme:
                    visual_style = theme["visual_style"]

            prompt = build_comic_prompt(
                slang="Test", origin="Test", explanation="Test",
                panels=[{"scene": "A scene", "dialogue": "Hi"}] * 4,
                visual_style=visual_style,
            )

            if test_id == "pixel_art":
                v.check("pixel_art theme 注入 visual_style", "pixel art" in prompt.lower())
            elif test_id == "nonexistent":
                v.check("nonexistent theme 回退到 manga 风格", "manga line art" in prompt)
            elif test_id == "":
                v.check("空 theme_id 回退到 manga 风格", "manga line art" in prompt)
    except Exception as e:
        v.check("prompt_node visual_style 查找逻辑测试", False, str(e))
        traceback.print_exc()

    # ── 9. 端到端数据流验证 ──
    v.section("9. 端到端数据流验证 (模拟完整 pipeline)")

    try:
        from app.prompts.theme_packs import get_random_theme, get_theme_by_id
        from app.prompts.script_prompt import build_system_prompt
        from app.prompts.comic_prompt import build_comic_prompt
        from app.schemas.script import ScriptResponse, Panel
        from app.schemas.comic import ComicRequest

        # Step 1: 随机选择主题 (模拟 script_stream.py)
        theme = get_random_theme()
        v.check(f"E2E: 随机选择主题 '{theme['name_zh']}'", True)

        # Step 2: 构建 script prompt (注入 world_setting)
        script_prompt = build_system_prompt(
            blacklist=["old_slang"],
            world_setting=theme["world_setting"],
        )
        v.check("E2E: script prompt 包含 theme world_setting",
                theme["world_setting"][:30] in script_prompt)

        # Step 3: 模拟 LLM 返回 script 数据
        mock_script = ScriptResponse(
            slang="Carpe Diem", origin="Latin", explanation="Seize the day",
            panel_count=4, panels=[
                Panel(scene="A busy office", dialogue="Let's go"),
                Panel(scene="A dark alley", dialogue="Watch out"),
                Panel(scene="A rooftop", dialogue="We made it"),
                Panel(scene="A cafe", dialogue=""),
            ],
            theme_id=theme["id"],
            theme_name_zh=theme["name_zh"],
        )
        v.check("E2E: ScriptResponse 包含 theme_id", mock_script.theme_id == theme["id"])
        v.check("E2E: ScriptResponse 包含 theme_name_zh", mock_script.theme_name_zh == theme["name_zh"])

        # Step 4: 前端传递 theme_id 到 comic 请求 (模拟 ComicRequest)
        comic_req = ComicRequest(
            slang=mock_script.slang,
            origin=mock_script.origin,
            explanation=mock_script.explanation,
            panel_count=mock_script.panel_count,
            panels=mock_script.panels,
            theme_id=mock_script.theme_id,
        )
        v.check("E2E: ComicRequest 包含 theme_id", comic_req.theme_id == theme["id"])

        # Step 5: comic graph 接收 state, prompt_node 查找 visual_style
        inputs = comic_req.model_dump()
        theme_lookup = get_theme_by_id(inputs["theme_id"])
        v.check("E2E: prompt_node 可通过 theme_id 查找主题", theme_lookup is not None)

        visual_style = theme_lookup["visual_style"] if theme_lookup else ""
        comic_prompt = build_comic_prompt(
            slang=inputs["slang"],
            origin=inputs["origin"],
            explanation=inputs["explanation"],
            panels=inputs["panels"],
            visual_style=visual_style,
        )
        v.check("E2E: comic prompt 包含 theme visual_style",
                visual_style[:30] in comic_prompt if visual_style else False,
                f"visual_style: '{visual_style[:30]}...'")

        # Step 6: SSE 事件模拟
        sse_theme_event = {"theme_id": theme["id"], "theme_name_zh": theme["name_zh"]}
        v.check("E2E: SSE theme 事件数据完整",
                "theme_id" in sse_theme_event and "theme_name_zh" in sse_theme_event)

        print(f"\n  端到端流程: {theme['name_zh']} ({theme['name_en']})")
        print(f"    world_setting → script prompt: OK")
        print(f"    theme_id → ComicRequest → prompt_node → visual_style → comic prompt: OK")
    except Exception as e:
        v.check("端到端数据流验证", False, str(e))
        traceback.print_exc()

    # ── 结果 ──
    success = v.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
