# 两阶段 LLM 调用优化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将单次 LLM 调用拆分为两阶段——快速分析返回 5 个主题，选中后内部 compose 详细 prompt 再生图。

**Architecture:** 新建 ANALYZE_PROMPT 和 COMPOSE_PROMPT 替换原 SYSTEM_PROMPT。analyze_service 只返回 name+brief。generate_service 内部新增 `_compose_prompt` 函数先调 LLM 生成详细 prompt，再调 Qwen 生图。前端去掉 prompt 字段传递。

**Tech Stack:** Python 3.12 / FastAPI / Pydantic v2 / httpx / React 19 / TypeScript

**Spec:** `docs/superpowers/specs/2026-03-31-two-stage-llm-design.md`

---

### Task 1: 新增错误码

**Files:**
- Modify: `backend/app/schemas/common.py`

- [ ] **Step 1: 在 ErrorCode 类中新增 compose 错误码**

在 `backend/app/schemas/common.py` 的 `ErrorCode` 类末尾添加：

```python
COMPOSE_LLM_FAILED = 50006
COMPOSE_LLM_INVALID = 50007
```

- [ ] **Step 2: 运行现有测试确认无破坏**

Run: `uv run pytest tests/backend/unit/ -v --tb=short`
Expected: 全部 PASS（ErrorCode 变更不影响现有测试）

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/common.py
git commit -m "chore: add COMPOSE_LLM_FAILED and COMPOSE_LLM_INVALID error codes"
```

---

### Task 2: 新建 ANALYZE_PROMPT

**Files:**
- Create: `backend/app/prompts/analyze_prompt.py`

- [ ] **Step 1: 创建 analyze_prompt.py**

```python
"""阶段 1 快速分析提示词 — 返回 5 个主题（name + brief）。"""

ANALYZE_PROMPT = """你是一位世界级的视觉艺术创意总监。你擅长从人物照片中发掘独特的创意方向。

## 角色

你是创意方向的发现者，而非提示词工程师。你的任务是从照片中捕捉灵感，提出最适合这个人物的主题方向。

## 任务

用户会发送一张人物照片。你需要：
1. 仔细观察照片中人物的姿态、表情、外貌特征、服装风格、整体氛围
2. 基于这些真实元素，自由构思 5 个创意主题方向
3. 为每个主题给出一个吸引人的名称和一句简短的卖点描述

## 创作方向引导

风格方向可以是但不限于：油画、水彩、赛博朋克、古典国画、极简主义、奇幻、写实摄影、波普艺术、浮世绘、哥特、蒸汽朋克、废土末日、太空歌剧、印象派、赛博禅意等任何方向。

关键：不要局限于上述方向。根据照片中人物的特征自由发挥，可以混合多种风格，创造独特的视觉概念。

## 核心原则

- 主题必须与照片中人物的形象、姿态、气质相关
- 5 个主题之间要有明显差异，覆盖不同风格方向
- 主题名称要有创意感，简练有力（2-6 个中文字）
- 描述要一句话打动用户，说明为什么这个主题适合照片中的人（30 字以内）

## 输出格式

你必须且只能输出以下 JSON 格式，不得包含任何额外文本、markdown 标记或注释：

{
  "options": [
    {"name": "主题名称", "brief": "一句话卖点描述"},
    {"name": "主题名称", "brief": "一句话卖点描述"},
    {"name": "主题名称", "brief": "一句话卖点描述"},
    {"name": "主题名称", "brief": "一句话卖点描述"},
    {"name": "主题名称", "brief": "一句话卖点描述"}
  ]
}

如果输出 JSON 后还有任何额外内容，整个回复将被视为无效。"""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/prompts/analyze_prompt.py
git commit -m "feat: add ANALYZE_PROMPT for stage 1 quick analysis"
```

---

### Task 3: 新建 COMPOSE_PROMPT

**Files:**
- Create: `backend/app/prompts/compose_prompt.py`

- [ ] **Step 1: 创建 compose_prompt.py**

```python
"""阶段 2 详细构图提示词 — 根据选中的主题生成完整英文构图 prompt。"""

COMPOSE_PROMPT = """你是一位世界级的 AI 绘画提示词工程师。你擅长将视觉概念转化为高质量的图像生成提示词。

## 角色

你是专业的构图设计师和提示词撰写专家。你的任务是将用户选定的创意主题，结合照片中人物的真实特征，撰写一个可用于图像生成的英文详细提示词。

## 任务

用户会提供：
1. 一张人物照片
2. 用户选中的主题名称和简述

你需要：
1. 仔细观察照片中人物的真实外貌特征（性别、年龄、发型、发色、肤色、体型、表情、姿态）
2. 基于选定的主题风格，为人物重新设计服装和道具（保留体型轮廓）
3. 设计与主题匹配的场景、光影、色彩方案
4. 撰写一个 200-400 词的英文提示词

## 写作规范

提示词必须覆盖以下维度：

- 【构图】画面比例感（cinematic wide shot / medium close-up / full body portrait 等），人物位置与主次关系
- 【光影】指定光源类型，须与风格一致（如赛博朋克→霓虹光，水墨→柔和漫射光，废土→硬阴影直射光）
- 【色彩】指定主色调、辅助色、点缀色，使用精确颜色词（如 deep sapphire blue / iridescent cyan / antique gold）
- 【人物外貌】必须基于照片真实内容：性别、年龄、发型发色、肤色、表情、身体姿态，保留核心特征
- 【服装道具】按主题风格重新设计服装但保留体型轮廓，描述材质细节
- 【场景氛围】描述背景环境、氛围元素（粒子/天气/自然元素）、空间层次、整体情绪
- 【镜头】指定镜头角度、焦距效果、运动感
- 【画质】必须包含：masterpiece, best quality, ultra-detailed, 8K resolution

## 重要约束

- 所有人物外貌描述必须基于照片实际内容，不得虚构照片中不存在的元素
- 服装按主题风格艺术化设计，但保留照片中人物的体型轮廓
- 提示词为纯英文
- 长度控制在 200-400 词之间

## 输出格式

你必须且只能输出以下 JSON 格式，不得包含任何额外文本、markdown 标记或注释：

{
  "prompt": "英文详细提示词（200-400词）"
}

如果输出 JSON 后还有任何额外内容，整个回复将被视为无效。"""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/prompts/compose_prompt.py
git commit -m "feat: add COMPOSE_PROMPT for stage 2 detailed composition"
```

---

### Task 4: 更新 Schema（TDD 红灯阶段）

**Files:**
- Modify: `backend/app/schemas/analyze.py`
- Modify: `backend/app/schemas/generate.py`

- [ ] **Step 1: 修改 StyleOption — 去掉 prompt 字段，更新 AnalyzeResponse**

将 `backend/app/schemas/analyze.py` 改为：

```python
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 编码的图片", min_length=1, max_length=5_000_000)
    image_format: str = Field(default="jpeg", description="图片格式", pattern=r"^(jpeg|png|webp)$")


class StyleOption(BaseModel):
    name: str = Field(..., description="主题名称（中文2-6字）")
    brief: str = Field(..., description="一句话卖点（中文30字以内）")


class AnalyzeResponse(BaseModel):
    options: list[StyleOption] = Field(..., description="主题选项列表", min_length=5, max_length=5)
```

- [ ] **Step 2: 修改 GenerateRequest — prompt 改为 style_brief**

将 `backend/app/schemas/generate.py` 改为：

```python
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 编码的原始照片", min_length=1)
    image_format: str = Field(default="jpeg", pattern=r"^(jpeg|png|webp)$")
    style_name: str = Field(..., description="选中的主题名称", min_length=1)
    style_brief: str = Field(..., description="选中的主题简述", min_length=1)


class GenerateResponse(BaseModel):
    poster_url: str = Field(..., description="海报图片的访问 URL")
    thumbnail_url: str = Field(..., description="缩略图访问 URL")
    history_id: str = Field(..., description="历史记录 ID")
```

- [ ] **Step 3: 运行后端单元测试确认红灯**

Run: `uv run pytest tests/backend/unit/ -v --tb=short`
Expected: 大量 FAIL — test_analyze 和 test_generate 的 mock 数据和断言都与旧 schema 绑定，需要重写

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/analyze.py backend/app/schemas/generate.py
git commit -m "refactor: update schemas for two-stage LLM flow"
```

---

### Task 5: 重写 analyze 单元测试

**Files:**
- Modify: `tests/backend/conftest.py`
- Modify: `tests/backend/unit/test_analyze.py`

- [ ] **Step 1: 更新 conftest.py — mock_llm_options 去掉 prompt 并扩展到 5 个，新增 mock_compose_response**

修改 `tests/backend/conftest.py`：

```python
@pytest.fixture
def mock_llm_options():
    return [
        {"name": "主题A", "brief": "描述A"},
        {"name": "主题B", "brief": "描述B"},
        {"name": "主题C", "brief": "描述C"},
        {"name": "主题D", "brief": "描述D"},
        {"name": "主题E", "brief": "描述E"},
    ]


@pytest.fixture
def mock_compose_response():
    return json.dumps({"prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, full body portrait of a person standing heroically in a cyberpunk city street at night, neon signs reflecting on wet pavement, cinematic wide shot, volumetric lighting, deep sapphire blue and iridescent cyan color palette, leather jacket and glowing accessories, rain particles, 85mm lens, shallow depth of field"})
```

- [ ] **Step 2: 完全重写 test_analyze.py**

```python
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.analyze_service import analyze_photo, AnalyzeError
from app.services.llm_client import LLMTimeoutError, LLMApiError


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.openai_api_key = "test-key"
    s.openai_base_url = "https://api.test.com/v4"
    s.openai_model = "test-model"
    s.vision_llm_max_tokens = 4096
    s.vision_llm_timeout = 60
    s.vision_llm_max_retries = 3
    return s


@pytest.fixture
def valid_llm_response(mock_llm_options):
    return json.dumps({"options": mock_llm_options})


# ------------------------------------------------------------------
# 正常流程
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_success_returns_5_options(mock_settings, valid_llm_response):
    """正常分析 — 返回 5 个风格选项"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            result = await analyze_photo("fake_b64_data", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[0].name == "主题A"
    assert result[1].brief == "描述B"


@pytest.mark.asyncio
async def test_analyze_options_have_name_and_brief_only(mock_settings, valid_llm_response):
    """返回的 StyleOption 只有 name 和 brief，无 prompt"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    for opt in result:
        assert hasattr(opt, "name")
        assert hasattr(opt, "brief")
        assert not hasattr(opt, "prompt"), "StyleOption 不应包含 prompt 字段"


@pytest.mark.asyncio
async def test_analyze_markdown_wrapped_json(mock_settings, mock_llm_options):
    """LLM 返回 ```json 包裹的 JSON — 应成功解析"""
    wrapped = f"```json\n{json.dumps({'options': mock_llm_options})}\n```"
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=wrapped):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[0].name == "主题A"


# ------------------------------------------------------------------
# 数量校验
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_fewer_than_5_raises_error(mock_settings, mock_llm_options):
    """LLM 返回少于 5 个选项 — 抛异常"""
    short_response = json.dumps({"options": mock_llm_options[:3]})
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=short_response):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "期望 5 个" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_more_than_5_truncates(mock_settings, mock_llm_options):
    """LLM 返回多于 5 个选项 — 只取前 5 个"""
    extra_options = mock_llm_options + [{"name": "多余", "brief": "这个不该出现"}]
    extra_response = json.dumps({"options": extra_options})
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=extra_response):
            result = await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert len(result) == 5
    assert result[4].name != "多余"


# ------------------------------------------------------------------
# LLM 错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_llm_timeout_raises_50001(mock_settings):
    """LLM 超时 — 返回 code 50001"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50001
    assert "Vision LLM 调用失败" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_llm_api_error_raises_50001(mock_settings):
    """LLM API 返回 4xx — 返回 code 50001"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMApiError("401")):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50001


# ------------------------------------------------------------------
# JSON 解析错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_invalid_json_raises_50002(mock_settings):
    """LLM 返回非 JSON — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value="not json"):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002


@pytest.mark.asyncio
async def test_analyze_missing_options_raises_50002(mock_settings):
    """JSON 缺少 options 字段 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"data": []}'):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "缺少 options 字段" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_empty_options_raises_50002(mock_settings):
    """options 为空数组 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"options": []}'):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002


@pytest.mark.asyncio
async def test_analyze_option_not_dict_raises_50002(mock_settings):
    """option 不是字典 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"options": ["string"]}'):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "不是有效对象" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_option_missing_name_raises_50002(mock_settings):
    """option 缺少 name — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=json.dumps({"options": [{"brief": "desc"}]})):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "name" in exc_info.value.message


@pytest.mark.asyncio
async def test_analyze_option_empty_brief_raises_50002(mock_settings):
    """option brief 为空 — code 50002"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=json.dumps({"options": [{"name": "主题", "brief": ""}]})):
            with pytest.raises(AnalyzeError) as exc_info:
                await analyze_photo("fake_b64", "jpeg", mock_settings)

    assert exc_info.value.code == 50002
    assert "brief" in exc_info.value.message


# ------------------------------------------------------------------
# Pydantic 验证
# ------------------------------------------------------------------

def test_analyze_empty_image_rejects(sample_image_base64):
    """空 image_base64 — 422"""
    from pydantic import ValidationError
    from app.schemas.analyze import AnalyzeRequest
    with pytest.raises(ValidationError):
        AnalyzeRequest(image_base64="", image_format="jpeg")


def test_analyze_invalid_format_rejects(sample_image_base64):
    """不支持的格式 — 422"""
    from pydantic import ValidationError
    from app.schemas.analyze import AnalyzeRequest
    with pytest.raises(ValidationError):
        AnalyzeRequest(image_base64=sample_image_base64, image_format="bmp")


# ------------------------------------------------------------------
# Endpoint 测试
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyze_endpoint_success(client, valid_llm_response, sample_image_base64):
    """POST /api/analyze 正常返回 5 个选项"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=valid_llm_response):
            resp = await client.post("/api/analyze", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]["options"]) == 5
    # 确认没有 prompt 字段
    assert "prompt" not in data["data"]["options"][0]


@pytest.mark.asyncio
async def test_analyze_endpoint_llm_error(client, sample_image_base64):
    """LLM 超时 — code 50001, HTTP 200"""
    with patch("app.services.analyze_service.LLMClient.__init__", return_value=None):
        with patch("app.services.analyze_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            resp = await client.post("/api/analyze", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
            })

    assert resp.status_code == 200
    assert resp.json()["code"] == 50001


@pytest.mark.asyncio
async def test_analyze_endpoint_missing_fields(client):
    """缺少必填字段 — 422"""
    resp = await client.post("/api/analyze", json={"image_format": "jpeg"})
    assert resp.status_code == 422
```

- [ ] **Step 3: 运行测试确认红灯**

Run: `uv run pytest tests/backend/unit/test_analyze.py -v --tb=short`
Expected: 全部 FAIL（analyze_service 还在用旧 SYSTEM_PROMPT 和旧逻辑）

- [ ] **Step 4: Commit**

```bash
git add tests/backend/conftest.py tests/backend/unit/test_analyze.py
git commit -m "test: update conftest fixtures and rewrite analyze unit tests"
```

---

### Task 6: 重写 generate 单元测试

**Files:**
- Modify: `tests/backend/unit/test_generate.py`

- [ ] **Step 1: 完全重写 test_generate.py**

```python
from pathlib import Path

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call

from app.schemas.generate import GenerateRequest
from app.services.generate_service import generate_artwork, GenerateError
from app.services.llm_client import LLMTimeoutError, LLMApiError
from app.services.image_gen_client import ImageGenTimeoutError, ImageGenApiError


# ------------------------------------------------------------------
# Pydantic 验证
# ------------------------------------------------------------------

def test_generate_valid_request(sample_image_base64):
    """有效的 GenerateRequest — 不再需要 prompt"""
    req = GenerateRequest(
        image_base64=sample_image_base64,
        image_format="jpeg",
        style_name="赛博朋克",
        style_brief="霓虹城市中的未来战士",
    )
    assert req.style_name == "赛博朋克"
    assert req.style_brief == "霓虹城市中的未来战士"


def test_generate_missing_style_name(sample_image_base64):
    """缺少 style_name — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            style_brief="desc",
            style_name="",
        )


def test_generate_missing_style_brief(sample_image_base64):
    """缺少 style_brief — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            style_name="赛博朋克",
            style_brief="",
        )


def test_generate_missing_image_base64():
    """image_base64 为空 — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64="",
            style_name="赛博朋克",
            style_brief="desc",
        )


def test_generate_invalid_format(sample_image_base64):
    """不支持的格式 — 422"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="gif",
            style_name="赛博朋克",
            style_brief="desc",
        )


def test_generate_has_no_prompt_field(sample_image_base64):
    """GenerateRequest 不再有 prompt 字段"""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GenerateRequest(
            image_base64=sample_image_base64,
            image_format="jpeg",
            prompt="old field",
            style_name="赛博朋克",
            style_brief="desc",
        )


# ------------------------------------------------------------------
# Service 层：调用顺序
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_calls_llm_compose_then_qwen(client, sample_image_base64, mock_image_gen_b64, mock_compose_response):
    """验证调用顺序：先 LLM compose → 再 Qwen 生图"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None) as mock_llm_init:
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response) as mock_llm_call:
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64) as mock_gen_call:
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "霓虹城市中的未来战士",
                    })

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    # LLM compose 被调用
    assert mock_llm_call.call_count == 1
    # Qwen 生图被调用
    assert mock_gen_call.call_count == 1
    # LLM 在 Qwen 之前调用
    llm_call_args = mock_llm_call.call_args
    assert "赛博朋克" in llm_call_args[0][4]  # user_text 包含 style_name


# ------------------------------------------------------------------
# Service 层：compose 错误处理
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_compose_timeout_raises_50006(client, sample_image_base64):
    """Compose LLM 超时 — code 50006"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, side_effect=LLMTimeoutError("timeout")):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50006
    assert "构图设计失败" in data["message"]


@pytest.mark.asyncio
async def test_generate_compose_invalid_json_raises_50007(client, sample_image_base64):
    """Compose LLM 返回无效 JSON — code 50007"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value="not json"):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50007


@pytest.mark.asyncio
async def test_generate_compose_missing_prompt_raises_50007(client, sample_image_base64):
    """Compose LLM 返回 JSON 但缺少 prompt 字段 — code 50007"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value='{"data": "no prompt"}'):
            resp = await client.post("/api/generate", json={
                "image_base64": sample_image_base64,
                "image_format": "jpeg",
                "style_name": "赛博朋克",
                "style_brief": "desc",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 50007


# ------------------------------------------------------------------
# Service 层：Qwen 生图错误
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_qwen_timeout_raises_50003(client, sample_image_base64, mock_compose_response):
    """Qwen 生图超时 — code 50003"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, side_effect=ImageGenTimeoutError("timeout")):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    assert resp.status_code == 200
    assert resp.json()["code"] == 50003


# ------------------------------------------------------------------
# Service 层：正常流程 + 副作用
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_success_returns_fields(client, sample_image_base64, mock_image_gen_b64, mock_compose_response):
    """正常生成 — 返回 poster_url, thumbnail_url, history_id"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "霓虹城市中的未来战士",
                    })

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["poster_url"].startswith("/data/posters/")
    assert data["thumbnail_url"].startswith("/data/posters/")
    assert "history_id" in data


@pytest.mark.asyncio
async def test_generate_creates_history(client, sample_image_base64, mock_image_gen_b64, mock_compose_response, tmp_data_dir):
    """生成成功后 history 中应有记录"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    assert resp.json()["code"] == 0
    history_id = resp.json()["data"]["history_id"]

    history_resp = await client.get("/api/history")
    history_data = history_resp.json()["data"]
    assert history_data["total"] >= 1
    assert any(item["id"] == history_id for item in history_data["items"])


@pytest.mark.asyncio
async def test_generate_saves_poster_files(client, sample_image_base64, mock_image_gen_b64, mock_compose_response, tmp_data_dir):
    """生成成功后保存海报和缩略图文件"""
    with patch("app.services.generate_service.LLMClient.__init__", return_value=None):
        with patch("app.services.generate_service.LLMClient.chat_with_vision", new_callable=AsyncMock, return_value=mock_compose_response):
            with patch("app.services.generate_service.ImageGenClient.__init__", return_value=None):
                with patch("app.services.generate_service.ImageGenClient.generate", new_callable=AsyncMock, return_value=mock_image_gen_b64):
                    resp = await client.post("/api/generate", json={
                        "image_base64": sample_image_base64,
                        "image_format": "jpeg",
                        "style_name": "赛博朋克",
                        "style_brief": "desc",
                    })

    data = resp.json()["data"]
    from app.config import get_settings
    settings = get_settings()
    poster_path = Path(settings.poster_storage_dir) / data["poster_url"].replace("/data/posters/", "")
    thumb_path = Path(settings.poster_storage_dir) / data["thumbnail_url"].replace("/data/posters/", "")
    assert poster_path.exists()
    assert thumb_path.exists()


# ------------------------------------------------------------------
# Endpoint 422
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_endpoint_missing_fields(client):
    """缺少必填字段 — 422"""
    resp = await client.post("/api/generate", json={"style_name": "test"})
    assert resp.status_code == 422
```

- [ ] **Step 2: 运行测试确认红灯**

Run: `uv run pytest tests/backend/unit/test_generate.py -v --tb=short`
Expected: 全部 FAIL（generate_service 还未改）

- [ ] **Step 3: Commit**

```bash
git add tests/backend/unit/test_generate.py
git commit -m "test: rewrite generate unit tests for two-stage LLM"
```

---

### Task 7: 重写 analyze_service.py（TDD 绿灯）

**Files:**
- Modify: `backend/app/services/analyze_service.py`

- [ ] **Step 1: 重写 analyze_service.py**

```python
import logging

from app.config import Settings
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError
from app.prompts.analyze_prompt import ANALYZE_PROMPT
from app.schemas.analyze import StyleOption

logger = logging.getLogger(__name__)


class AnalyzeError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
    """分析照片，返回 5 个主题选项（仅名称+简述）。"""
    llm = LLMClient(settings)
    try:
        logger.info("LLM 分析请求开始 (model=%s)", settings.openai_model)
        content = await llm.chat_with_vision(
            ANALYZE_PROMPT, image_base64, image_format,
            "请分析照片中的人物，生成 5 个创意主题选项",
            temperature=0.8,
        )
        logger.info("LLM 分析完成")
    except (LLMTimeoutError, LLMApiError) as e:
        logger.error("LLM 调用失败: %s", e)
        raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        logger.error("LLM 响应解析失败: %s", e)
        raise AnalyzeError(50002, f"Vision LLM 返回格式异常: {e}") from e

    if not isinstance(data, dict) or "options" not in data:
        raise AnalyzeError(50002, "JSON 缺少 options 字段")

    options = data["options"]
    if not isinstance(options, list) or len(options) == 0:
        raise AnalyzeError(50002, "options 应为非空数组")

    if len(options) < 5:
        raise AnalyzeError(50002, f"LLM 返回 {len(options)} 个选项，期望 5 个")

    style_options = []
    for i, opt in enumerate(options[:5]):
        if not isinstance(opt, dict):
            raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
        for field in ("name", "brief"):
            if field not in opt or not opt[field]:
                raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
        style_options.append(StyleOption(name=opt["name"], brief=opt["brief"]))
    return style_options
```

- [ ] **Step 2: 运行 analyze 测试确认绿灯**

Run: `uv run pytest tests/backend/unit/test_analyze.py -v --tb=short`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analyze_service.py
git commit -m "feat: rewrite analyze_service for two-stage LLM (5 topics, no prompt)"
```

---

### Task 8: 重写 generate_service.py + routers/generate.py（TDD 绿灯）

**Files:**
- Modify: `backend/app/services/generate_service.py`
- Modify: `backend/app/routers/generate.py`

- [ ] **Step 1: 重写 generate_service.py**

```python
import logging

from app.config import Settings
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError
from app.prompts.compose_prompt import COMPOSE_PROMPT
from app.services.image_gen_client import ImageGenClient, ImageGenTimeoutError, ImageGenApiError
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.schemas.common import ErrorCode

logger = logging.getLogger(__name__)


class GenerateError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def _compose_prompt(
    image_base64: str, image_format: str,
    style_name: str, style_brief: str, settings: Settings,
) -> str:
    """调 LLM 为选中的主题生成详细英文构图 prompt。"""
    llm = LLMClient(settings)
    try:
        logger.info("Compose LLM 请求开始 (model=%s, style=%s)", settings.openai_model, style_name)
        content = await llm.chat_with_vision(
            COMPOSE_PROMPT, image_base64, image_format,
            f"主题: {style_name}\n简述: {style_brief}\n请为这个主题撰写详细的英文构图提示词。",
            temperature=0.7,
        )
    except (LLMTimeoutError, LLMApiError) as e:
        logger.error("Compose LLM 调用失败: %s", e)
        raise GenerateError(ErrorCode.COMPOSE_LLM_FAILED, f"构图设计失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        logger.error("Compose LLM 响应解析失败: %s", e)
        raise GenerateError(ErrorCode.COMPOSE_LLM_INVALID, f"构图设计响应异常: {e}") from e

    if "prompt" not in data or not data["prompt"]:
        raise GenerateError(ErrorCode.COMPOSE_LLM_INVALID, "构图设计缺少 prompt 字段")
    return data["prompt"]


async def generate_artwork(
    image_base64: str, image_format: str,
    style_name: str, style_brief: str,
    settings: Settings, storage: FileStorage, history: HistoryService,
) -> dict:
    """生成海报：先 LLM 构思详细 prompt，再调 Qwen 生图。"""
    # 1. 保存原始照片
    photo_info = storage.save_photo(image_base64, image_format)

    # 2. Compose — LLM 生成详细英文构图 prompt
    prompt = await _compose_prompt(image_base64, image_format, style_name, style_brief, settings)

    # 3. Image generation — Qwen 生图
    gen_client = ImageGenClient(settings)
    try:
        logger.info("图片生成请求开始 (model=%s, style=%s)", settings.qwen_image_model, style_name)
        poster_b64 = await gen_client.generate(prompt, image_base64, image_format)
        logger.info("图片生成完成")
    except (ImageGenTimeoutError, ImageGenApiError) as e:
        logger.error("图片生成失败: %s", e)
        raise GenerateError(50003, f"图片生成失败: {e}") from e
    except Exception as e:
        logger.error("生成结果处理失败: %s", e)
        raise GenerateError(50004, f"生成结果处理失败: {e}") from e

    # 4. Save poster & record history
    poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])
    history_id = history.add({
        "style_name": style_name,
        "prompt": prompt,
        "poster_url": poster_info["poster_url"],
        "thumbnail_url": poster_info["thumbnail_url"],
        "photo_url": photo_info["url"],
    })
    logger.info("海报已保存 (history_id=%s)", history_id)
    return {
        "poster_url": poster_info["poster_url"],
        "thumbnail_url": poster_info["thumbnail_url"],
        "history_id": history_id,
    }
```

- [ ] **Step 2: 更新 routers/generate.py**

将 `generate_endpoint` 中的调用从 `request.prompt` 改为 `request.style_brief`：

```python
import logging

from fastapi import APIRouter, Depends
from app.schemas.generate import GenerateRequest
from app.schemas.common import ApiResponse, ErrorCode
from app.config import get_settings, Settings
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.services.generate_service import generate_artwork, GenerateError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=ApiResponse)
async def generate_endpoint(request: GenerateRequest, settings: Settings = Depends(get_settings)):
    logger.info("收到生成请求 (style=%s)", request.style_name)
    storage = FileStorage(settings.photo_storage_dir, settings.poster_storage_dir)
    history = HistoryService(settings.history_file, settings.max_history_records)
    try:
        result = await generate_artwork(
            request.image_base64, request.image_format,
            request.style_name, request.style_brief,
            settings, storage, history,
        )
        logger.info("生成完成, poster_url=%s", result.get("poster_url", ""))
        return ApiResponse(code=0, message="success", data=result)
    except GenerateError as e:
        logger.error("生成失败: %s", e.message)
        return ApiResponse(code=e.code, message=e.message, data=None)
    except Exception as e:
        logger.error("生成异常: %s", e, exc_info=True)
        return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
```

- [ ] **Step 3: 运行全部后端单元测试确认绿灯**

Run: `uv run pytest tests/backend/unit/ -v --tb=short`
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/generate_service.py backend/app/routers/generate.py
git commit -m "feat: rewrite generate_service with compose LLM + update router"
```

---

### Task 9: 删除旧 system_prompt.py + 重写 test_system_prompt.py

**Files:**
- Delete: `backend/app/prompts/system_prompt.py`
- Modify: `tests/backend/unit/test_system_prompt.py`（重写为验证新 prompt）

- [ ] **Step 1: 确认没有其他文件引用 system_prompt**

Run: `grep -r "system_prompt" backend/ --include="*.py" -l`

如果只剩 `system_prompt.py` 本身，安全删除。如果还有其他引用，先修复。

- [ ] **Step 2: 删除旧 system_prompt.py**

```bash
rm backend/app/prompts/system_prompt.py
```

- [ ] **Step 3: 重写 test_system_prompt.py — 验证新 prompt 常量**

```python
import pytest

from app.prompts.analyze_prompt import ANALYZE_PROMPT
from app.prompts.compose_prompt import COMPOSE_PROMPT


def test_analyze_prompt_exists():
    """ANALYZE_PROMPT 应存在且非空"""
    assert ANALYZE_PROMPT
    assert len(ANALYZE_PROMPT) > 100


def test_analyze_prompt_contains_key_elements():
    """ANALYZE_PROMPT 应包含关键要素"""
    assert "5" in ANALYZE_PROMPT
    assert "options" in ANALYZE_PROMPT
    assert "name" in ANALYZE_PROMPT
    assert "brief" in ANALYZE_PROMPT
    # 不应包含旧的固定风格池
    assert "武侠江湖" not in ANALYZE_PROMPT


def test_compose_prompt_exists():
    """COMPOSE_PROMPT 应存在且非空"""
    assert COMPOSE_PROMPT
    assert len(COMPOSE_PROMPT) > 100


def test_compose_prompt_contains_key_elements():
    """COMPOSE_PROMPT 应包含关键维度"""
    assert "prompt" in COMPOSE_PROMPT
    assert "masterpiece" in COMPOSE_PROMPT
    assert "200-400" in COMPOSE_PROMPT
```

- [ ] **Step 4: 运行全部后端单元测试**

Run: `uv run pytest tests/backend/unit/ -v --tb=short`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git rm backend/app/prompts/system_prompt.py
git add tests/backend/unit/test_system_prompt.py
git commit -m "refactor: remove old SYSTEM_PROMPT, verify new prompts in tests"
```

---

### Task 10: 前端适配

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/StyleSelection/StyleSelection.tsx`
- Modify: `frontend/src/constants/index.ts`
- Modify: `frontend/src/services/api.test.ts`
- Modify: `frontend/src/components/StyleCard/StyleCard.test.tsx`
- Modify: `frontend/src/components/StyleSelection/StyleSelection.test.tsx`

- [ ] **Step 1: 修改 types/index.ts — StyleOption 去 prompt**

将 `StyleOption` 改为：

```typescript
export interface StyleOption {
  name: string;
  brief: string;
}
```

- [ ] **Step 2: 修改 services/api.ts — generatePoster 参数**

将 `generatePoster` 函数签名改为 `(photoBase64, styleName, styleBrief)`，body 中 `prompt` 改为 `style_brief`：

```typescript
export async function generatePoster(
  photoBase64: string,
  styleName: string,
  styleBrief: string,
): Promise<GenerateResponse> {
  return request<GenerateResponse>(
    API_ENDPOINTS.GENERATE,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: photoBase64,
        image_format: 'jpeg',
        style_name: styleName,
        style_brief: styleBrief,
      }),
    },
    TIMEOUTS.GENERATE_REQUEST,
  );
}
```

- [ ] **Step 3: 修改 App.tsx — handleSelectStyle 和 handleRegenerate**

`handleSelectStyle`（约第 145 行）：
```typescript
const response = await generatePoster(photo, style.name, style.brief);
```

`handleRegenerate`（约第 186 行）：
```typescript
const response = await generatePoster(photo, selectedOption.name, selectedOption.brief);
```

- [ ] **Step 4: 修改 App.tsx — 更新 Generating 状态提示文案**

将第 309 行的提示文案改为：
```tsx
<p className="text-gray-500 text-sm">AI 构思构图 + 生成图片中，通常需要 30-90 秒</p>
```

- [ ] **Step 5: 修改 StyleSelection.tsx — 网格布局适配 5 卡片**

将第 76 行的 grid 改为：
```tsx
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
```

- [ ] **Step 6: 修改 constants/index.ts — 调大 generate timeout**

```typescript
GENERATE_REQUEST: 400_000,
```

- [ ] **Step 7: 修改 api.test.ts — generatePoster 测试适配新参数**

将 generatePoster describe 块中的变量和断言改为：

```typescript
const base64 = 'aGVsbG8=';
const styleName = 'cyberpunk';
const styleBrief = 'future tech warrior';

// 测试调用：
await generatePoster(base64, styleName, styleBrief);

// 断言 body 包含：
expect(parsed).toEqual({
  image_base64: base64,
  image_format: 'jpeg',
  style_name: styleName,
  style_brief: styleBrief,
});
```

同时修改 `successBody` 中的 analyze options mock 去掉 prompt 字段：
```typescript
const successBody = {
  code: 0,
  message: 'ok',
  data: { options: [{ name: 'style1', brief: 'b' }] },
};
```

- [ ] **Step 8: 修改 StyleCard.test.tsx — 去 prompt 字段**

将第 6-10 行的 mockStyle 改为：
```typescript
const mockStyle: StyleOption = {
  name: '赛博朋克',
  brief: '未来科技感风格',
};
```

- [ ] **Step 9: 修改 StyleSelection.test.tsx — 去 prompt 字段，扩展到 5 个**

将第 6-10 行的 mockStyles 改为：
```typescript
const mockStyles: StyleOption[] = [
  { name: '赛博朋克', brief: '未来科技感' },
  { name: '水墨画', brief: '中国古典风格' },
  { name: '波普艺术', brief: '流行色彩' },
  { name: '油画', brief: '古典写实' },
  { name: '浮世绘', brief: '日本传统风格' },
];
```

- [ ] **Step 10: 运行前端单元测试确认通过**

Run: `cd frontend && npx vitest run`
Expected: 全部 PASS

- [ ] **Step 11: 运行前端构建确认无类型错误**

Run: `cd frontend && npm run build`
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 12: Commit**

```bash
git add frontend/src/
git commit -m "feat: adapt frontend for two-stage LLM flow"
```

---

### Task 11: 重写真实 API 集成测试

**Files:**
- Modify: `tests/backend/integration/test_real_api.py`

- [ ] **Step 1: 重写 test_real_api.py**

```python
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
_backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.insert(0, str(_backend_dir))
project_root = _backend_dir.parent

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
```

- [ ] **Step 2: 运行单元测试确认不影响**

Run: `uv run pytest tests/backend/unit/ -v --tb=short`
Expected: 全部 PASS

- [ ] **Step 3: Commit**

```bash
git add tests/backend/integration/test_real_api.py
git commit -m "test: rewrite integration tests for two-stage LLM flow"
```

---

### Task 12: 全量验证 + 最终检查

**Files:** 无新增/修改

- [ ] **Step 1: 运行全部后端单元测试**

Run: `uv run pytest tests/backend/unit/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端构建**

Run: `cd frontend && npm run build`
Expected: 构建成功

- [ ] **Step 3: 运行前端 lint**

Run: `cd frontend && npm run lint`
Expected: 无错误

- [ ] **Step 4: 最终 commit（如有残留修改）**

```bash
git add -A
git commit -m "chore: final cleanup for two-stage LLM flow"
```
