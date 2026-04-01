# 两阶段 LLM 调用优化设计

> 日期: 2026-03-31
> 状态: Draft
> 作者: Claude + User

---

## 1. 背景与问题

### 当前流程

```
拍照 → POST /api/analyze → LLM 一次生成 3 个风格选项(含完整 prompt ×3)
     → 用户选择 → POST /api/generate(prompt) → Qwen 生图
```

### 痛点

1. **慢**: 单次 LLM 调用要求一次性生成 3 个 200-400 词的完整英文 prompt，响应耗时长
2. **不灵活**: 系统提示词预设了 10 个固定风格池（武侠、赛博朋克、暗黑童话等），限制创意空间
3. **浪费**: 用户只选 1 个风格，另外 2 个完整 prompt 白白生成

## 2. 目标

1. 分析阶段快速返回，用户等待时间显著缩短
2. 取消固定风格池，基于照片中人物的形象/姿态/氛围自由创作主题
3. 只为用户选中的那一个主题生成详细构图 prompt，节省 token 和时间
4. TDD 开发，测试策略前置，验收标准明确

## 3. 设计方案

### 3.1 新流程

```
拍照 → POST /api/analyze → LLM 快速分析 → 返回 5 个主题(只有 name + brief)
     → 用户选择 → POST /api/generate(style_name + style_brief)
                 → 内部: LLM 详细构图(prompt×1) → Qwen 生图 → 返回结果
```

### 3.2 系统提示词设计

#### ANALYZE_PROMPT（阶段 1 — 快速分析）

**文件**: `backend/app/prompts/analyze_prompt.py`

**设计要点**:
- 取消固定 10 个风格池
- 提供方向性引导：可以是油画、水彩、赛博朋克、古典国画、极简主义、奇幻、写实摄影风格等任何方向
- 核心要求：必须基于照片中人物的形象、姿态、表情、服装、氛围来推导最合适的主题
- 输出 5 个选项，每个只有 name + brief
- brief 控制在 30 字以内的卖点描述

**输出格式**:
```json
{
  "options": [
    { "name": "主题名（中文2-6字）", "brief": "一句话卖点（中文30字以内）" },
    ...共 5 个
  ]
}
```

#### COMPOSE_PROMPT（阶段 2 — 详细构图设计）

**文件**: `backend/app/prompts/compose_prompt.py`

**设计要点**:
- 输入：照片 + 主题名称 + 简短描述
- 输出：单个 200-400 词的英文构图 prompt
- 覆盖维度：构图/光影/色彩/人物外貌/服装道具/场景氛围/镜头/画质
- 人物描述必须基于照片实际内容
- 服装按主题风格重新设计但保留体型轮廓

**输出格式**:
```json
{ "prompt": "英文详细提示词（200-400词）" }
```

**可读性要求**:
- prompt 文件内结构化分段，每段有注释标记
- 角色定义 → 任务描述 → 输入说明 → 写作规范 → 输出格式，各段清晰分隔

### 3.3 Schema 变更

#### schemas/analyze.py

```python
class StyleOption(BaseModel):
    name: str = Field(..., description="主题名称（中文2-6字）")
    brief: str = Field(..., description="一句话卖点（中文30字以内）")
    # prompt 字段已移除

class AnalyzeResponse(BaseModel):
    options: list[StyleOption] = Field(..., description="主题选项列表", min_length=5, max_length=5)
```

> **注意**: `min_length=5, max_length=5` 严格要求恰好 5 个选项。服务层也做二次校验。

#### schemas/generate.py

```python
class GenerateRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 编码的原始照片", min_length=1)
    image_format: str = Field(default="jpeg", pattern=r"^(jpeg|png|webp)$")
    style_name: str = Field(..., description="选中的主题名称", min_length=1)
    style_brief: str = Field(..., description="选中的主题简述", min_length=1)
    # prompt 字段已移除 — 后端内部 compose 生成

class GenerateResponse(BaseModel):
    # 不变
    poster_url: str
    thumbnail_url: str
    history_id: str
```

#### schemas/history.py（向后兼容）

`HistoryItem` 的 `prompt` 字段**保留**，但语义变更为"后端 compose 生成的 prompt"。旧数据中 `prompt` 是前端传入的，新数据中是后端生成的，读取端无影响。

`generate_service.py` 中 `history.add(...)` 传入 compose 生成的 prompt：

```python
history_id = history.add({
    "style_name": style_name,
    "prompt": prompt,  # compose 阶段生成的详细 prompt
    "poster_url": poster_info["poster_url"],
    "thumbnail_url": poster_info["thumbnail_url"],
    "photo_url": photo_info["url"],
})
```

### 3.4 服务层变更

#### analyze_service.py

```python
async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
    """分析照片，返回 5 个主题选项（仅名称+简述）。"""
    llm = LLMClient(settings)
    try:
        content = await llm.chat_with_vision(
            ANALYZE_PROMPT, image_base64, image_format,
            "请分析照片中的人物，生成 5 个创意主题选项",
            temperature=0.8,
        )
    except (LLMTimeoutError, LLMApiError) as e:
        raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        raise AnalyzeError(50002, f"Vision LLM 返回格式异常: {e}") from e

    # 校验结构
    if not isinstance(data, dict) or "options" not in data:
        raise AnalyzeError(50002, "JSON 缺少 options 字段")
    options = data["options"]
    if not isinstance(options, list) or len(options) == 0:
        raise AnalyzeError(50002, "options 应为非空数组")

    # 严格要求恰好 5 个选项
    if len(options) < 5:
        raise AnalyzeError(50002, f"LLM 返回 {len(options)} 个选项，期望 5 个")

    # 构造 StyleOption 列表
    style_options = []
    for i, opt in enumerate(options[:5]):  # 最多取 5 个
        if not isinstance(opt, dict):
            raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
        for field in ("name", "brief"):
            if field not in opt or not opt[field]:
                raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
        style_options.append(StyleOption(name=opt["name"], brief=opt["brief"]))
    return style_options
```

#### generate_service.py

```python
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError

# 新增错误码（定义在 schemas/common.py 的 ErrorCode 类中统一管理）
# COMPOSE_LLM_FAILED = 50006    # Compose LLM 调用失败
# COMPOSE_LLM_INVALID = 50007   # Compose LLM 响应解析失败

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
        raise GenerateError(COMPOSE_LLM_FAILED, f"构图设计失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        logger.error("Compose LLM 响应解析失败: %s", e)
        raise GenerateError(COMPOSE_LLM_INVALID, f"构图设计响应异常: {e}") from e

    if "prompt" not in data or not data["prompt"]:
        raise GenerateError(COMPOSE_LLM_INVALID, "构图设计缺少 prompt 字段")
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
        raise GenerateError(50003, f"图片生成失败: {e}") from e
    except Exception as e:
        raise GenerateError(50004, f"生成结果处理失败: {e}") from e

    # 4. Save poster & record history
    poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])
    history_id = history.add({
        "style_name": style_name,
        "prompt": prompt,  # compose 生成的详细 prompt
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

**可读性设计**: compose 和 image gen 各用独立函数，职责单一。

### 3.5 路由层变更

#### routers/generate.py

- `GenerateRequest` 适配新字段（`style_name` + `style_brief`，无 `prompt`）
- 内部调用 `generate_artwork` 传参对应调整

### 3.6 前端变更

#### types/index.ts

```typescript
export interface StyleOption {
  name: string;
  brief: string;
  // prompt 已移除
}
```

#### services/api.ts

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

#### App.tsx

- **handleSelectStyle**: 调用 `generatePoster(photoBase64, style.name, style.brief)`，不再传 `style.prompt`
- **handleRegenerate**: 同样改为 `generatePoster(photoBase64, selectedOption.name, selectedOption.brief)`，不再依赖 `selectedOption.prompt`

#### StyleSelection / StyleCard

- 卡片只展示 `name` + `brief`
- 5 个卡片的网格布局需适配（当前 `grid-cols-3` 对 5 个不对称），建议使用 `flex flex-wrap gap-4` 或 `grid grid-cols-2 md:grid-cols-3` 响应式布局

#### constants/index.ts

- `TIMEOUTS.GENERATE_REQUEST` 需调大：新流程包含 compose LLM + Qwen 生图两次调用，总耗时更长

### 3.7 文件结构变化

```
backend/app/prompts/
├── system_prompt.py          → 删除
├── analyze_prompt.py         → 新增（ANALYZE_PROMPT）
└── compose_prompt.py         → 新增（COMPOSE_PROMPT）
```

## 4. 测试策略与验收标准

### 4.1 TDD 开发顺序

```
1. 先写 analyze 阶段单元测试（红）→ 实现（绿）→ 重构
2. 先写 compose+generate 阶段单元测试（红）→ 实现（绿）→ 重构
3. 写真实 API 集成测试 → 逐个验证通过
4. 前端适配
```

### 4.2 阶段 1：Analyze 单元测试

| 测试用例 | 验收标准 |
|----------|----------|
| `test_analyze_returns_5_style_options` | 返回恰好 5 个 StyleOption |
| `test_analyze_option_has_name_and_brief_only` | 每个 option 只有 name + brief，无 prompt |
| `test_analyze_option_brief_within_limit` | 每个 brief ≤ 30 字 |
| `test_analyze_llm_failure_raises_error` | LLM 调用失败 → AnalyzeError(50001) |
| `test_analyze_invalid_json_raises_error` | JSON 解析失败 → AnalyzeError(50002) |
| `test_analyze_missing_options_raises_error` | 缺少 options 字段 → 异常 |
| `test_analyze_empty_options_raises_error` | options 为空 → 异常 |

### 4.3 阶段 2：Compose + Generate 单元测试

| 测试用例 | 验收标准 |
|----------|----------|
| `test_generate_calls_llm_compose_then_qwen` | 验证调用顺序：先 LLM → 再 Qwen |
| `test_generate_compose_receives_style_context` | LLM 请求包含 style_name + style_brief |
| `test_generate_compose_failure_raises_error` | LLM 构图失败 → GenerateError(50006) |
| `test_generate_compose_invalid_response_raises_error` | LLM 响应解析失败 → GenerateError(50007) |
| `test_generate_image_gen_failure_raises_error` | Qwen 生图失败 → GenerateError(50003) |
| `test_generate_saves_photo_and_poster` | 文件存储流程正确 |
| `test_generate_returns_expected_fields` | 返回 poster_url, thumbnail_url, history_id |

### 4.4 真实 API 集成测试

**Analyze 阶段**:

| 测试用例 | 验收标准 |
|----------|----------|
| `test_real_analyze_returns_5_topics` | 真实调 GLM-4.6V，返回 5 个有意义的不同主题 |
| `test_real_analyze_topics_are_diverse` | 5 个主题之间有明显差异 |
| `test_real_analyze_topics_match_photo` | 主题与照片内容相关 |
| `test_real_analyze_response_time` | 响应时间 < 10s |
| `test_real_analyze_no_preset_styles` | 不局限于原 10 个固定风格 |

**Compose + Generate 阶段**:

| 测试用例 | 验收标准 |
|----------|----------|
| `test_real_compose_generates_english_prompt` | LLM 返回 200-400 词英文 prompt |
| `test_real_compose_prompt_describes_person` | prompt 包含对照片人物的具体描述 |
| `test_real_generate_end_to_end` | 选主题 → 完整走通 → 拿到 poster_url |
| `test_real_generate_poster_is_valid_image` | 生成的海报是有效图片 |

### 4.5 提示词质量集成测试

| 测试用例 | 验收标准 |
|----------|----------|
| `test_real_analyze_creative_diversity` | 多次调用，主题有创意多样性 |
| `test_real_compose_prompt_structure` | prompt 包含构图/光影/色彩/人物/场景/镜头/画质维度 |

## 5. 影响范围总结

| 文件 | 改动类型 |
|------|----------|
| `prompts/analyze_prompt.py` | 新建 |
| `prompts/compose_prompt.py` | 新建 |
| `prompts/system_prompt.py` | 删除 |
| `schemas/analyze.py` | StyleOption 去 prompt，AnalyzeResponse min_length=5 |
| `schemas/generate.py` | prompt → style_brief |
| `schemas/history.py` | 无变更（prompt 字段保留，语义变为 compose 生成） |
| `schemas/common.py` | 新增 COMPOSE_LLM_FAILED=50006, COMPOSE_LLM_INVALID=50007 |
| `services/analyze_service.py` | 改用 ANALYZE_PROMPT，解析 5 个 |
| `services/generate_service.py` | 新增 LLMClient 依赖 + `_compose_prompt` 函数 |
| `routers/analyze.py` | 无变更（prompt 引用在 service 层） |
| `routers/generate.py` | 适配新请求字段 |
| `frontend/src/types/index.ts` | StyleOption 去 prompt |
| `frontend/src/services/api.ts` | generatePoster 参数变更 |
| `frontend/src/App.tsx` | handleSelectStyle + handleRegenerate 传参调整 |
| `frontend/src/components/StyleSelection/` | 网格布局适配 5 个卡片 |
| `frontend/src/constants/index.ts` | GENERATE_REQUEST timeout 调大 |
| `tests/backend/unit/*` | 全部重写对应单元测试 |
| `tests/backend/integration/test_real_api.py` | 重写集成测试 |
| `frontend/src/services/api.test.ts` | generatePoster 测试参数变更 |
