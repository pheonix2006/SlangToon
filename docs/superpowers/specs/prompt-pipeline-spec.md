# Pose Art Generator — Prompt Pipeline Spec

> 版本: v1.0
> 日期: 2026-03-28
> 关联设计文档: `2026-03-28-pose-art-generator-design.md`

---

## A. 系统提示词（System Prompt）完整内容

### A.1 角色设定

你是一位世界级的视觉艺术总监与 AI 绘画提示词工程师。你擅长分析人物照片中的姿态、表情、服饰和场景元素，并将这些真实元素转化为令人惊艳的艺术创作概念。你的工作流程是：仔细观察照片中的每一个细节，然后基于这些真实细节，生成可以直接用于 AI 图像生成模型的高质量提示词。

### A.2 风格方向池

以下为 10 个可选风格方向，Vision LLM 应从中选取 3 个最适合当前照片人物气质的风格，并确保每个选项的风格各不相同：

| # | 风格名称 | 英文标识 | 核心特征描述 |
|---|---------|---------|-------------|
| 1 | **武侠江湖** | `wuxia` | 水墨渲染的山川背景，飘逸的汉服衣袂，古风建筑或竹林，刀剑光影，武侠电影般的动态构图，中国传统色彩体系（朱砂、靛蓝、藤黄） |
| 2 | **赛博朋克** | `cyberpunk` | 霓虹灯光晕染的黑暗城市街道，全息广告牌，机械义体改造元素，雨夜反射的地面，高对比度冷色调（青蓝 + 品红 + 亮黄），充满科技感的服装与配饰 |
| 3 | **暗黑童话** | `dark_fairy_tale` | 哥特式城堡或幽暗森林背景，月光透射的神秘氛围，华丽而略带诡异的服饰，荆棘/玫瑰/迷雾等装饰元素，深紫 + 暗金 + 炭黑的色彩组合 |
| 4 | **水墨仙侠** | `ink_xianxia` | 留白构图的传统水墨画风格，云雾缭绕的仙山，道袍或轻纱，灵气环绕的光效，淡墨晕染的渐变层次，仙鹤/莲花等元素点缀，整体空灵飘逸 |
| 5 | **机甲战场** | `mecha` | 巨大的机械装甲与人物融合，钢铁与碳纤维质感，火花四溅的战场，戏剧性的仰角镜头，金属冷灰 + 警示橙的配色，HUD 全息界面元素 |
| 6 | **魔法学院** | `magic_academy` | 霍格沃茨式或东方魔法学院场景，华丽的巫师长袍或校服，漂浮的魔法阵与发光符文，古老图书馆或天文塔，温暖烛光 + 神秘紫光，羊皮纸与水晶道具 |
| 7 | **废土末日** | `wasteland` | 荒芜的沙漠或废墟城市，做旧磨损的皮革与金属装备，防毒面具与破旧披风，夕阳或沙尘暴的强烈氛围，铁锈橙 + 军绿 + 沙黄色的末日色系 |
| 8 | **深海探索** | `deep_sea` | 深海发光生物点缀的幽蓝水下世界，气泡与光线折射，潜水服或美人鱼化的服饰，珊瑚与沉船的神秘场景，生物荧光的蓝绿光效，空灵梦幻的氛围 |
| 9 | **蒸汽朋克** | `steampunk` | 维多利亚时代的复古未来主义，齿轮与蒸汽管道装饰，黄铜与皮革的材质质感，飞艇或钟塔场景，暖棕 + 黄铜金 + 蒸汽白的色调，精密机械配件 |
| 10 | **星际远航** | `space_opera` | 浩瀚星空与星云背景，光滑的未来主义太空服，飞船驾驶舱或外星球地表，宇宙尘埃与星光照耀，深空蓝 + 银白 + 星光金，全息投影界面 |

### A.3 输出 JSON Schema

Vision LLM **必须** 严格以如下 JSON 格式输出，不得包含任何额外的 markdown 标记、解释文本或注释：

```json
{
  "options": [
    {
      "name": "风格名称（中文，2-6字）",
      "brief": "给用户看的简略描述（一句话，20字以内，突出最吸引人的效果）",
      "prompt": "给生图模型的详细提示词（英文，200-400词）"
    },
    {
      "name": "...",
      "brief": "...",
      "prompt": "..."
    },
    {
      "name": "...",
      "brief": "...",
      "prompt": "..."
    }
  ]
}
```

**字段约束：**

| 字段 | 类型 | 长度 | 语言 | 说明 |
|------|------|------|------|------|
| `name` | string | 2-6 字 | 中文 | 风格标签名称，简洁有力 |
| `brief` | string | ≤20 字 | 中文 | 面向用户的卖点描述，激发点击欲 |
| `prompt` | string | 200-400 词 | 英文 | 可直接用于生图 API 的完整提示词 |
| `options` | array | 固定 3 个元素 | — | 3 个风格必须互不相同 |

### A.4 生图提示词（prompt）写作规范

`prompt` 字段是整个管线的核心产物，必须遵循以下写作规范。**所有描述必须基于照片中的实际内容**，不得虚构照片中不存在的元素。

#### A.4.1 构图（Composition）

- 明确主次关系：人物为主体，场景为背景
- 指定画面比例感（如 `cinematic wide shot`、`medium close-up`、`full body portrait`）
- 描述人物在画面中的位置（center-framed / rule of thirds / dynamic diagonal）
- 如有多人合照，需描述各人物的空间关系

#### A.4.2 光影（Lighting）

- 根据风格指定光源类型：`neon rim lighting` / `moonlit` / `golden hour sunlight` / `dramatic side lighting` / `volumetric fog rays` / `bioluminescent glow` 等
- 必须与风格方向一致（赛博朋克 → 霓虹光；水墨仙侠 → 柔和漫射光；废土 → 硬阴影直射光）
- 描述光影对人物的塑造效果（轮廓光 / 面部高光 / 阴影层次）

#### A.4.3 色彩（Color）

- 指定主色调、辅助色、点缀色
- 使用风格方向池中的推荐配色为基础，可适度调整
- 使用精确的颜色描述词：`deep sapphire blue`、`burnt sienna`、`iridescent cyan`、`antique gold` 等
- 描述整体色彩情绪：`moody desaturated palette`、`vibrant high-contrast`、`muted earth tones`

#### A.4.4 人物外貌（Character Appearance）

- **必须基于照片真实内容**：性别、大致年龄、发型发色、肤色
- 保留照片中人物的核心特征，但允许按风格进行艺术化改造
- 描述面部表情（需与照片表情一致或合理延伸）
- 身体姿态（需与照片姿势一致，包括手势、站立/坐姿、身体朝向）

#### A.4.5 服装道具（Costume & Props）

- 根据风格方向重新设计服装，但必须保留照片人物的体型轮廓
- 描述服装材质与细节（丝绸的飘逸感 / 皮革的粗犷质感 / 金属的冷冽光泽）
- 如照片中有可见的道具（手机、眼镜、包等），需按风格进行艺术化转化
- 风格化配饰：武器、魔法道具、机械部件等，须与人物姿态自然融合

#### A.4.6 场景氛围（Scene & Atmosphere）

- 描述背景环境，需与风格方向一致
- 增添氛围元素：粒子效果（火花/光点/尘埃）、天气（雨/雾/雪/沙尘）、自然元素（水波/云层/藤蔓）
- 描述空间深度与层次感（前景遮挡物 / 中景主体 / 远景背景）
- 指定整体情绪氛围（`epic and cinematic`、`mysterious and ethereal`、`gritty and raw`）

#### A.4.7 镜头语言（Camera & Lens）

- 指定镜头角度：`low angle heroic shot`、`bird's eye view`、`dutch angle`、`over-the-shoulder`
- 描述焦距效果：`shallow depth of field`（浅景深虚化）、`wide-angle distortion`（广角畸变）、`telephoto compression`（长焦压缩）
- 运动感描述：`motion blur on background`、`freeze-frame action shot`、`slow shutter light trail`

#### A.4.8 画质词（Quality Tags）

- 必须包含的基础画质词：`masterpiece`、`best quality`、`ultra-detailed`、`8K resolution`
- 风格化画质词（按需选择）：`photorealistic` / `oil painting style` / `digital art` / `concept art` / `illustration` / `cinematic still`
- 渲染引擎暗示（按需）：`Unreal Engine 5 render`、`Octane render`、`ray tracing`

### A.5 完整系统提示词文本

以下是可直接用于 API 调用的完整系统提示词：

```
你是一位世界级的视觉艺术总监与 AI 绘画提示词工程师。你擅长分析人物照片中的姿态、表情、服饰和场景元素，并将这些真实元素转化为令人惊艳的艺术创作概念。

## 你的任务

用户会发送一张人物照片。你需要：
1. 仔细观察照片中人物的姿态、表情、外貌、服装、场景等所有细节
2. 从下方风格方向池中选取 3 个最适合该人物气质与姿态的风格（3个风格必须互不相同）
3. 为每个风格撰写一个详细的英文图像生成提示词（prompt）

## 风格方向池

1. 武侠江湖（wuxia）：水墨渲染山川、飘逸汉服、古风建筑或竹林、刀剑光影、武侠电影动态构图、中国传统色彩（朱砂/靛蓝/藤黄）
2. 赛博朋克（cyberpunk）：霓虹灯城市街道、全息广告牌、机械义体、雨夜反射地面、高对比度冷色调（青蓝/品红/亮黄）、科技感服装配饰
3. 暗黑童话（dark_fairy_tale）：哥特城堡或幽暗森林、月光神秘氛围、华丽诡异服饰、荆棘/玫瑰/迷雾装饰、深紫/暗金/炭黑配色
4. 水墨仙侠（ink_xianxia）：留白水墨构图、云雾仙山、道袍轻纱、灵气光效、淡墨晕染渐变、仙鹤莲花点缀、空灵飘逸
5. 机甲战场（mecha）：机械装甲融合、钢铁碳纤维质感、火花战场、仰角镜头、金属冷灰/警示橙配色、HUD全息界面
6. 魔法学院（magic_academy）：魔法学院场景、华丽巫师长袍/校服、漂浮魔法阵与发光符文、古老图书馆/天文塔、温暖烛光+神秘紫光、羊皮纸水晶道具
7. 废土末日（wasteland）：荒芜沙漠/废墟城市、做旧皮革金属装备、防毒面具破旧披风、夕阳/沙尘暴氛围、铁锈橙/军绿/沙黄色系
8. 深海探索（deep_sea）：深海发光生物点缀的幽蓝水下世界、气泡光线折射、潜水服/美人鱼化服饰、珊瑚沉船场景、生物荧光蓝绿光效、空灵梦幻
9. 蒸汽朋克（steampunk）：维多利亚复古未来主义、齿轮蒸汽管道、黄铜皮革材质、飞艇/钟塔场景、暖棕/黄铜金/蒸汽白色调、精密机械配件
10. 星际远航（space_opera）：浩瀚星空星云、光滑未来主义太空服、飞船驾驶舱/外星球、宇宙尘埃星光照耀、深空蓝/银白/星光金、全息投影界面

## 提示词写作规范（prompt 字段）

你为每个风格生成的 prompt 必须是英文，200-400词，包含以下维度：

- 【构图】明确画面比例感（cinematic wide shot / medium close-up / full body portrait），人物位置与主次关系
- 【光影】指定光源类型，须与风格一致（赛博朋克→霓虹光，水墨→柔和漫射光，废土→硬阴影直射光）
- 【色彩】指定主色调、辅助色、点缀色，使用精确颜色词（deep sapphire blue / iridescent cyan / antique gold）
- 【人物外貌】必须基于照片真实内容：性别、年龄、发型发色、肤色、表情、身体姿态，保留核心特征
- 【服装道具】按风格重新设计服装但保留体型轮廓，描述材质细节，照片中的道具按风格艺术化转化
- 【场景氛围】描述背景环境、氛围元素（粒子/天气/自然元素）、空间层次、整体情绪
- 【镜头】指定镜头角度、焦距效果、运动感
- 【画质】必须包含：masterpiece, best quality, ultra-detailed, 8K resolution；按需添加风格化画质词和渲染引擎暗示

重要：所有人物描述必须基于照片实际内容，不得虚构照片中不存在的元素。

## 输出格式

你必须且只能输出以下 JSON 格式，不得包含任何额外文本、markdown标记或注释：

{
  "options": [
    {
      "name": "风格名称（中文2-6字）",
      "brief": "一句话卖点描述（中文20字以内）",
      "prompt": "英文详细提示词（200-400词）"
    },
    {
      "name": "...",
      "brief": "...",
      "prompt": "..."
    },
    {
      "name": "...",
      "brief": "...",
      "prompt": "..."
    }
  ]
}

如果输出 JSON 后还有任何额外内容，整个回复将被视为无效。
```

---

## B. Vision LLM 调用规格

### B.1 概述

Vision LLM 负责"看图说话"——接收用户照片，基于系统提示词分析照片内容，输出结构化的风格选项 JSON。

### B.2 消息格式（OpenAI Chat Completion）

采用 OpenAI Chat Completion API 的标准消息格式，使用 OpenAI-compatible 端点。

#### 请求结构

```python
# 伪代码，展示消息构建逻辑
messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT  # 见 A.5 完整系统提示词
    },
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image_string}"
                }
            },
            {
                "type": "text",
                "text": "请分析照片中的人物，生成 3 个创意风格选项"
            }
        ]
    }
]
```

#### 完整 HTTP 请求示例

```python
import httpx
import base64
import json

async def call_vision_llm(base64_image: str, config: VisionLLMConfig) -> dict:
    """调用 Vision LLM 分析照片并返回风格选项"""
    url = f"{config.base_url}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config.model_name,  # 如 "gpt-4o", "qwen-vl-max" 等
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    },
                    {
                        "type": "text",
                        "text": "请分析照片中的人物，生成 3 个创意风格选项"
                    }
                ]
            }
        ],
        "temperature": 0.8,       # 适度创造性
        "max_tokens": 4096,       # 3 个风格选项需要足够的 token
        "response_format": { "type": "json_object" }  # 如果模型支持
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
```

### B.3 图片 Base64 传入

**前端处理流程：**

```
Canvas.toDataURL("image/jpeg", 0.85)
  → data:image/jpeg;base64,/9j/4AAQ...
  → 提取逗号后的纯 base64 字符串
  → 通过 HTTP POST JSON body 发送到后端
```

**后端接收与转发：**

```python
from pydantic import BaseModel

class AnalyzeRequest(BaseModel):
    image_base64: str  # 纯 base64 字符串，不含 data URI 前缀

class AnalyzeResponse(BaseModel):
    options: list[StyleOption]

class StyleOption(BaseModel):
    name: str
    brief: str
    prompt: str
```

**图片规格约束：**

| 属性 | 要求 |
|------|------|
| 格式 | JPEG |
| 编码 | Base64（URL-safe 或 standard 均可，代码统一转换为 standard） |
| 质量 | JPEG quality 0.85 |
| 分辨率建议 | 长边 ≤ 1536px（前端 Canvas 缩放后截取） |
| 最大体积 | ≤ 4MB（base64 编码后 ≤ 5.3MB） |

### B.4 模型参数

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `model` | `gpt-4o` / `qwen-vl-max`（可配置） | 通过 `.env` 的 `VISION_LLM_MODEL` 配置 |
| `temperature` | `0.8` | 适度创造性，让风格选项有差异化的同时保持质量 |
| `max_tokens` | `4096` | 3 个完整提示词需要充足的输出空间 |
| `top_p` | `0.95` | （可选）配合 temperature 控制多样性 |
| `response_format` | `{"type": "json_object"}` | 如果模型支持，强制 JSON 输出 |
| `timeout` | `60s` | HTTP 请求超时时间 |

### B.5 响应解析

```python
import json
import re

def parse_vision_response(api_response: dict) -> list[dict]:
    """
    解析 Vision LLM API 响应，提取风格选项列表。

    Args:
        api_response: OpenAI Chat Completion API 原始响应

    Returns:
        风格选项列表 [{"name": ..., "brief": ..., "prompt": ...}, ...]

    Raises:
        ValueError: 响应格式无效或 JSON 解析失败
    """
    # 1. 提取 assistant 回复内容
    choices = api_response.get("choices", [])
    if not choices:
        raise ValueError("API 响应中没有 choices")

    content = choices[0].get("message", {}).get("content", "")

    # 2. 清理可能的 markdown 代码块包裹
    content = content.strip()
    if content.startswith("```"):
        # 移除 ```json 和 ``` 包裹
        content = re.sub(r'^```(?:json)?\s*\n?', '', content)
        content = re.sub(r'\n?```\s*$', '', content)

    # 3. 解析 JSON
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Vision LLM 输出不是有效的 JSON: {e}\n原始内容: {content[:500]}")

    # 4. 校验结构
    if not isinstance(data, dict) or "options" not in data:
        raise ValueError("JSON 结构缺少 'options' 字段")

    options = data["options"]
    if not isinstance(options, list) or len(options) != 3:
        raise ValueError(f"options 必须是包含 3 个元素的数组，实际: {len(options) if isinstance(options, list) else type(options)}")

    # 5. 校验每个选项的字段
    required_fields = {"name", "brief", "prompt"}
    for i, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValueError(f"options[{i}] 不是对象")
        missing = required_fields - set(option.keys())
        if missing:
            raise ValueError(f"options[{i}] 缺少字段: {missing}")
        if not option["name"] or not option["brief"] or not option["prompt"]:
            raise ValueError(f"options[{i}] 存在空字段")

    return options
```

### B.6 异常处理

```python
from enum import Enum

class VisionLLMError(Enum):
    TIMEOUT = "vision_llm_timeout"          # 请求超时
    AUTH_FAILED = "vision_llm_auth_failed"   # 认证失败 (401/403)
    RATE_LIMIT = "vision_llm_rate_limited"   # 限流 (429)
    INVALID_RESPONSE = "vision_llm_invalid_response"  # 响应格式无效
    MODEL_ERROR = "vision_llm_model_error"   # 模型内部错误 (5xx)
    NETWORK_ERROR = "vision_llm_network_error"  # 网络连接失败


async def safe_call_vision_llm(base64_image: str, config: VisionLLMConfig) -> list[dict]:
    """带完整异常处理的 Vision LLM 调用"""
    try:
        response = await call_vision_llm(base64_image, config)
        return parse_vision_response(response)

    except httpx.TimeoutException:
        raise VisionLLMError.TIMEOUT

    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            raise VisionLLMError.AUTH_FAILED
        elif e.response.status_code == 429:
            # 可选: 指数退避重试
            raise VisionLLMError.RATE_LIMIT
        elif e.response.status_code >= 500:
            raise VisionLLMError.MODEL_ERROR
        else:
            raise VisionLLMError.NETWORK_ERROR

    except (json.JSONDecodeError, ValueError) as e:
        raise VisionLLMError.INVALID_RESPONSE

    except httpx.ConnectError:
        raise VisionLLMError.NETWORK_ERROR
```

**前端错误映射表：**

| 错误码 | 前端展示 | 建议操作 |
|--------|---------|---------|
| `TIMEOUT` | "分析超时，请稍后重试" | 显示重试按钮 |
| `AUTH_FAILED` | "服务配置错误" | 不展示重试（需管理员处理） |
| `RATE_LIMIT` | "请求过于频繁，请等待后重试" | 显示倒计时后启用重试 |
| `INVALID_RESPONSE` | "AI 分析结果异常，请重试" | 自动重试一次 |
| `MODEL_ERROR` | "AI 服务暂时不可用" | 显示重试按钮 |
| `NETWORK_ERROR` | "网络连接失败，请检查网络" | 显示重试按钮 |

---

## C. Qwen Image 2.0 调用规格

### C.1 API 端点与认证

```
基础 URL: https://dashscope.aliyuncs.com/compatible-mode/v1
图像生成端点: POST /images/generations
认证方式: Bearer Token（Header）
```

**环境变量配置：**

```env
# .env
QWEN_API_KEY=sk-xxxxxxxxxxxxxxxx
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_IMAGE_MODEL=qwen-image-2.0
```

### C.2 请求格式（图生图模式）

使用 OpenAI-compatible 的图像生成 API，以参考图（ref_image）+ 文本提示词的方式进行图生图。

```python
import httpx
import base64

async def call_qwen_image(base64_image: str, prompt: str, config: QwenImageConfig) -> dict:
    """调用 Qwen Image 2.0 进行图生图"""

    url = f"{config.base_url}/images/generations"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": config.model_name,  # "qwen-image-2.0"
        "input": {
            "prompt": prompt,
            "ref_image": f"data:image/jpeg;base64,{base64_image}"
        },
        "parameters": {
            "n": 1,                   # 生成图片数量
            "size": "1024*1024",      # 输出尺寸（宽*高）
            "ref_strength": 0.7,      # 参考图影响强度 (0.0-1.0)，0.7 保持人物相似度
            "seed": -1                # 随机种子，-1 为随机
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
```

### C.3 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | string | `qwen-image-2.0` | 模型标识 |
| `input.prompt` | string | — | 用户选中的风格提示词（英文，由 Vision LLM 生成） |
| `input.ref_image` | string | — | 参考照片的 Data URI（`data:image/jpeg;base64,...`） |
| `parameters.n` | int | `1` | 每次生成图片数量 |
| `parameters.size` | string | `"1024*1024"` | 输出尺寸，格式为 `宽*高` |
| `parameters.ref_strength` | float | `0.7` | 参考图影响强度。0.0 = 完全忽略参考图（纯文生图），1.0 = 极度贴近参考图。0.7 平衡创意性与人物还原度 |
| `parameters.seed` | int | `-1` | 随机种子。-1 随机，固定值可复现 |

**尺寸选项参考：**

| 值 | 用途 |
|----|------|
| `1024*1024` | 正方形海报（默认，适合社交媒体） |
| `768*1344` | 竖版海报（适合手机壁纸/分享） |
| `1344*768` | 横版海报（适合桌面壁纸） |

### C.4 响应解析

```python
def parse_qwen_image_response(api_response: dict) -> str:
    """
    解析 Qwen Image 2.0 API 响应，提取生成的图片 URL 或 Base64。

    Args:
        api_response: Qwen Image API 原始响应

    Returns:
        生成的图片 URL 或 Base64 数据

    Raises:
        ValueError: 响应格式无效
    """
    # 方式 1: OpenAI compatible 格式 — data 数组
    if "data" in api_response:
        data_list = api_response["data"]
        if not data_list:
            raise ValueError("API 响应 data 数组为空")
        first_item = data_list[0]
        # 优先取 url，其次取 b64_json
        if "url" in first_item:
            return first_item["url"]
        elif "b64_json" in first_item:
            return f"data:image/png;base64,{first_item['b64_json']}"
        else:
            raise ValueError("data[0] 中没有 url 或 b64_json 字段")

    # 方式 2: DashScope 原生格式 — output.results
    elif "output" in api_response:
        results = api_response["output"].get("results", [])
        if not results:
            raise ValueError("API 响应 output.results 为空")
        return results[0].get("url", "")

    else:
        raise ValueError(f"未知的 API 响应格式: {list(api_response.keys())}")
```

### C.5 超时与重试策略

```python
import asyncio

MAX_RETRIES = 3
INITIAL_BACKOFF = 2.0   # 首次重试等待 2 秒
MAX_BACKOFF = 10.0      # 最大等待 10 秒
REQUEST_TIMEOUT = 120.0  # 图像生成超时 120 秒
GENERATION_POLL_INTERVAL = 3.0  # 异步任务轮询间隔


async def call_qwen_image_with_retry(
    base64_image: str,
    prompt: str,
    config: QwenImageConfig
) -> dict:
    """带指数退避重试的 Qwen Image 调用"""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            return await call_qwen_image(base64_image, prompt, config)

        except httpx.TimeoutException:
            last_error = "timeout"
            # 图像生成超时不应盲目重试，直接抛出
            raise

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # 限流: 指数退避重试
                backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                last_error = f"rate_limited (retry in {backoff}s)"
                await asyncio.sleep(backoff)
                continue
            elif e.response.status_code >= 500:
                # 服务端错误: 指数退避重试
                backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
                last_error = f"server_error_{e.response.status_code} (retry in {backoff}s)"
                await asyncio.sleep(backoff)
                continue
            else:
                # 客户端错误: 不重试
                raise

        except httpx.ConnectError:
            backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
            last_error = f"network_error (retry in {backoff}s)"
            await asyncio.sleep(backoff)
            continue

    raise RuntimeError(f"Qwen Image 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")
```

**重试策略总结：**

| 错误类型 | 是否重试 | 等待策略 | 最大重试 |
|---------|---------|---------|---------|
| 超时 (Timeout) | 否 | — | 0 |
| 限流 (429) | 是 | 指数退避 2s → 4s → 8s | 3 |
| 服务端错误 (5xx) | 是 | 指数退避 2s → 4s → 8s | 3 |
| 网络连接失败 | 是 | 指数退避 2s → 4s → 8s | 3 |
| 客户端错误 (4xx 非 429) | 否 | — | 0 |

---

## D. 两次调用衔接

### D.1 整体数据流

```
[前端拍照]
    │  JPEG Base64
    ▼
[POST /api/analyze]  ← 照片 Base64
    │
    ├─► [Vision LLM]  ← System Prompt + 照片 Base64
    │       │
    │       ▼
    │   JSON: { options: [{name, brief, prompt}, ...] }
    │       │
    │       ▼
    │   [parse_vision_response()]  ← 校验 + 清洗
    │       │
    ▼       ▼
[前端展示风格卡片]  ← [{name, brief, prompt}, ...]
    │
    │  用户选择第 N 个选项
    ▼
[POST /api/generate]  ← 照片 Base64 + options[N].prompt
    │
    ├─► [Qwen Image 2.0]  ← ref_image (照片) + prompt (文字)
    │       │
    │       ▼
    │   { data: [{url / b64_json}] }
    │       │
    │       ▼
    │   [parse_qwen_image_response()]  ← 提取图片
    │       │
    ▼       ▼
[前端展示海报]  ← 图片 URL / Base64
```

### D.2 后端 API 接口衔接

#### `/api/analyze` 接口

```python
@app.post("/api/analyze")
async def analyze_photo(request: AnalyzeRequest) -> AnalyzeResponse:
    """分析照片，返回风格选项"""
    # 1. 调用 Vision LLM
    raw_response = await safe_call_vision_llm(request.image_base64, vision_config)

    # 2. 解析响应
    options = parse_vision_response(raw_response)

    # 3. 存储会话（Redis / 内存缓存，TTL 30 分钟）
    session_id = generate_session_id()
    session_data = {
        "image_base64": request.image_base64,  # 保存原图供后续生图使用
        "options": options,
        "created_at": datetime.now().isoformat()
    }
    await cache.set(f"session:{session_id}", session_data, ttl=1800)

    # 4. 返回风格选项（不返回 prompt 给前端显示，但传给前端供后续选择提交）
    return AnalyzeResponse(
        session_id=session_id,
        options=options  # 包含 prompt 字段
    )
```

#### `/api/generate` 接口

```python
@app.post("/api/generate")
async def generate_artwork(request: GenerateRequest) -> GenerateResponse:
    """根据选中的风格生成海报"""
    # 1. 获取会话数据
    session_data = await cache.get(f"session:{request.session_id}")
    if not session_data:
        raise HTTPException(status_code=404, detail="会话已过期，请重新拍照")

    # 2. 校验选择索引
    index = request.selected_index
    if index < 0 or index >= len(session_data["options"]):
        raise HTTPException(status_code=400, detail="无效的风格选择")

    # 3. 提取 prompt 与原图
    prompt = session_data["options"][index]["prompt"]
    image_base64 = session_data["image_base64"]

    # 4. 调用 Qwen Image
    raw_response = await call_qwen_image_with_retry(image_base64, prompt, qwen_config)

    # 5. 解析响应
    image_result = parse_qwen_image_response(raw_response)

    # 6. 保存历史记录
    history_item = {
        "session_id": request.session_id,
        "style_name": session_data["options"][index]["name"],
        "prompt": prompt,
        "image_url_or_base64": image_result,
        "created_at": datetime.now().isoformat()
    }
    await save_history(history_item)

    return GenerateResponse(image=image_result, style_name=history_item["style_name"])
```

### D.3 Prompt 提取与传递

**关键原则：`prompt` 字段在后端全程保持完整，前端仅作展示用。**

```
Vision LLM 输出 → parse_vision_response() 校验
    → 存储在后端会话中（完整 prompt）
    → /api/analyze 返回给前端（前端需要完整 prompt 用于 /api/generate 请求）
    → 前端用户选择时，将选中索引 (selected_index) + session_id 提交
    → 后端根据 session_id 找到完整 prompt，传给 Qwen Image
```

**Prompt 传递安全约束：**

1. `prompt` 在前端展示时不可被用户编辑（MVP 阶段）
2. 后端必须校验 `prompt` 非空且长度在合理范围（200-400 词）
3. 前端传递 `selected_index`（0-2），而非 prompt 本身，防止前端篡改

### D.4 照片格式保持

| 环节 | 格式 | 说明 |
|------|------|------|
| 前端 Canvas 截取 | JPEG (quality 0.85) | `canvas.toDataURL("image/jpeg", 0.85)` |
| 前端 → 后端传输 | JPEG Base64 | 通过 JSON body |
| 后端 → Vision LLM | JPEG Base64 | Data URI 格式 `data:image/jpeg;base64,...` |
| 后端 → Qwen Image | JPEG Base64 | Data URI 格式 `data:image/jpeg;base64,...` |
| 后端缓存 | JPEG Base64 | Redis / 内存缓存，存储原始 Base64 |
| Qwen Image 输出 | PNG URL 或 Base64 | 根据 API 返回格式，通常为 PNG |
| 后端 → 前端返回 | PNG URL 或 Base64 | 直接透传 |

---

## E. 验收标准

### E.1 各环节通过标准

| 环节 | 通过标准 |
|------|---------|
| **系统提示词** | Vision LLM 在 10 次调用中至少 9 次返回合法 JSON；`prompt` 字段 100% 包含构图/光影/色彩/人物/服装/场景/镜头/画质描述 |
| **Vision LLM 调用** | 正常请求在 30s 内返回；超时/错误场景正确抛出对应错误码；响应解析不崩溃 |
| **响应解析** | 能处理：标准 JSON、markdown 代码块包裹的 JSON、尾部有额外空白的 JSON；对畸形 JSON 抛出明确错误 |
| **风格选项校验** | 恰好 3 个选项；每个选项有 name/brief/prompt 三个字段；3 个选项风格互不相同 |
| **Qwen Image 调用** | 正常请求在 90s 内返回图片；限流/服务端错误自动重试；超时不重试直接报错 |
| **会话衔接** | 同一照片可成功完成 analyze → generate 全流程；30 分钟后 session 过期；无效 session_id 返回 404 |
| **照片格式** | JPEG 格式全程不降级；Base64 编解码无损；输出图片可直接展示和下载 |

### E.2 pytest 测试脚本模板

#### E.2.1 Mock 测试（Vision LLM 响应解析）

```python
# tests/test_vision_parser.py
"""Vision LLM 响应解析单元测试"""

import json
import pytest
from app.services.vision_parser import parse_vision_response


class TestParseVisionResponse:
    """测试 Vision LLM 响应解析器"""

    # --- 正常情况 ---

    def test_parse_standard_json(self):
        """标准 JSON 响应应正确解析"""
        mock_options = [
            {
                "name": "赛博朋克",
                "brief": "霓虹都市中的未来战士",
                "prompt": "A cinematic cyberpunk portrait, masterpiece, best quality..."
            },
            {
                "name": "水墨仙侠",
                "brief": "飘逸如仙的古代侠客",
                "prompt": "An ethereal ink wash painting style portrait, masterpiece..."
            },
            {
                "name": "废土末日",
                "brief": "荒芜世界的孤胆英雄",
                "prompt": "A gritty wasteland portrait, masterpiece, best quality..."
            }
        ]
        api_response = {
            "choices": [
                {"message": {"content": json.dumps({"options": mock_options})}}
            ]
        }

        result = parse_vision_response(api_response)

        assert len(result) == 3
        assert result[0]["name"] == "赛博朋克"
        assert "masterpiece" in result[0]["prompt"]
        assert "best quality" in result[1]["prompt"]

    def test_parse_markdown_wrapped_json(self):
        """Markdown 代码块包裹的 JSON 应正确清理和解析"""
        content = '```json\n{"options": [{"name": "测试", "brief": "描述", "prompt": "test prompt masterpiece"}]}\n```'
        api_response = {
            "choices": [{"message": {"content": content}}]
        }

        # 选项数量不足 3 个应抛出 ValueError
        with pytest.raises(ValueError, match="3 个元素"):
            parse_vision_response(api_response)

    def test_parse_three_valid_options(self):
        """三个选项的 markdown 包裹 JSON 应正确解析"""
        content = '```json\n{"options": [{"name": "A", "brief": "B", "prompt": "P1 masterpiece best quality ultra-detailed 8K"}, {"name": "C", "brief": "D", "prompt": "P2 masterpiece best quality ultra-detailed 8K"}, {"name": "E", "brief": "F", "prompt": "P3 masterpiece best quality ultra-detailed 8K"}]}\n```'
        api_response = {
            "choices": [{"message": {"content": content}}]
        }

        result = parse_vision_response(api_response)
        assert len(result) == 3

    # --- 异常情况 ---

    def test_empty_choices_raises(self):
        """空 choices 应抛出 ValueError"""
        api_response = {"choices": []}
        with pytest.raises(ValueError, match="choices"):
            parse_vision_response(api_response)

    def test_invalid_json_raises(self):
        """非法 JSON 应抛出 ValueError 并包含上下文信息"""
        api_response = {
            "choices": [{"message": {"content": "这不是JSON"}}]
        }
        with pytest.raises(ValueError, match="有效的 JSON"):
            parse_vision_response(api_response)

    def test_missing_options_field_raises(self):
        """缺少 options 字段应抛出 ValueError"""
        api_response = {
            "choices": [{"message": {"content": json.dumps({"data": []})}}]
        }
        with pytest.raises(ValueError, match="options"):
            parse_vision_response(api_response)

    def test_wrong_option_count_raises(self):
        """选项数量不为 3 应抛出 ValueError"""
        options = [{"name": f"风格{i}", "brief": f"描述{i}", "prompt": f"prompt {i}"} for i in range(2)]
        api_response = {
            "choices": [{"message": {"content": json.dumps({"options": options})}}]
        }
        with pytest.raises(ValueError, match="3"):
            parse_vision_response(api_response)

    def test_missing_field_in_option_raises(self):
        """选项缺少必要字段应抛出 ValueError"""
        options = [
            {"name": "风格1", "brief": "描述1"},  # 缺少 prompt
            {"name": "风格2", "brief": "描述2", "prompt": "p2"},
            {"name": "风格3", "brief": "描述3", "prompt": "p3"},
        ]
        api_response = {
            "choices": [{"message": {"content": json.dumps({"options": options})}}]
        }
        with pytest.raises(ValueError, match="缺少字段"):
            parse_vision_response(api_response)

    def test_empty_field_in_option_raises(self):
        """选项字段为空字符串应抛出 ValueError"""
        options = [
            {"name": "风格1", "brief": "描述1", "prompt": "p1"},
            {"name": "", "brief": "描述2", "prompt": "p2"},  # name 为空
            {"name": "风格3", "brief": "描述3", "prompt": "p3"},
        ]
        api_response = {
            "choices": [{"message": {"content": json.dumps({"options": options})}}]
        }
        with pytest.raises(ValueError, match="空字段"):
            parse_vision_response(api_response)

    # --- 画质词检查 ---

    def test_prompt_contains_quality_tags(self):
        """prompt 字段应包含必要的画质词"""
        mock_options = [
            {"name": "风格1", "brief": "描述1", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, a beautiful portrait"},
            {"name": "风格2", "brief": "描述2", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, cinematic shot"},
            {"name": "风格3", "brief": "描述3", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, digital art"},
        ]
        api_response = {
            "choices": [{"message": {"content": json.dumps({"options": mock_options})}}]
        }
        result = parse_vision_response(api_response)

        required_tags = ["masterpiece", "best quality", "ultra-detailed", "8K"]
        for option in result:
            for tag in required_tags:
                assert tag in option["prompt"], f"缺少画质词: {tag}"
```

#### E.2.2 Mock 测试（Qwen Image 响应解析）

```python
# tests/test_qwen_parser.py
"""Qwen Image 2.0 响应解析单元测试"""

import pytest
from app.services.qwen_parser import parse_qwen_image_response


class TestParseQwenImageResponse:
    """测试 Qwen Image API 响应解析器"""

    def test_parse_openai_compatible_url(self):
        """OpenAI compatible 格式应正确提取 URL"""
        mock_url = "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/xxx.png"
        api_response = {
            "data": [{"url": mock_url}]
        }

        result = parse_qwen_image_response(api_response)
        assert result == mock_url

    def test_parse_openai_compatible_b64_json(self):
        """OpenAI compatible 格式应正确提取 Base64"""
        mock_b64 = "iVBORw0KGgoAAAANSUhEUg..."
        api_response = {
            "data": [{"b64_json": mock_b64}]
        }

        result = parse_qwen_image_response(api_response)
        assert result.startswith("data:image/png;base64,")
        assert mock_b64 in result

    def test_parse_dashscope_native_format(self):
        """DashScope 原生格式应正确解析"""
        mock_url = "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/yyy.png"
        api_response = {
            "output": {"results": [{"url": mock_url}]}
        }

        result = parse_qwen_image_response(api_response)
        assert result == mock_url

    def test_empty_data_raises(self):
        """空 data 数组应抛出 ValueError"""
        api_response = {"data": []}
        with pytest.raises(ValueError, match="为空"):
            parse_qwen_image_response(api_response)

    def test_unknown_format_raises(self):
        """未知响应格式应抛出 ValueError"""
        api_response = {"unexpected_key": "value"}
        with pytest.raises(ValueError, match="未知的"):
            parse_qwen_image_response(api_response)

    def test_data_item_missing_url_and_b64_raises(self):
        """data 项缺少 url 和 b64_json 应抛出 ValueError"""
        api_response = {"data": [{"other_field": "value"}]}
        with pytest.raises(ValueError, match="url"):
            parse_qwen_image_response(api_response)
```

#### E.2.3 Mock 测试（Vision LLM 客户端）

```python
# tests/test_vision_client.py
"""Vision LLM 客户端 Mock 测试"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.vision_client import safe_call_vision_llm, VisionLLMConfig, VisionLLMError


@pytest.fixture
def mock_config():
    return VisionLLMConfig(
        base_url="https://api.example.com",
        api_key="sk-test-key",
        model_name="test-vision-model"
    )


@pytest.fixture
def valid_options():
    return [
        {"name": "风格1", "brief": "描述1", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt 1"},
        {"name": "风格2", "brief": "描述2", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt 2"},
        {"name": "风格3", "brief": "描述3", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt 3"},
    ]


class TestVisionClient:

    @pytest.mark.asyncio
    async def test_successful_call(self, mock_config, valid_options):
        """正常调用应返回解析后的选项列表"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({"options": valid_options})}}]
        }

        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await safe_call_vision_llm("fake_base64", mock_config)

        assert len(result) == 3
        assert result[0]["name"] == "风格1"

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, mock_config):
        """超时应抛出 TIMEOUT 错误"""
        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(VisionLLMError.TIMEOUT):
                await safe_call_vision_llm("fake_base64", mock_config)

    @pytest.mark.asyncio
    async def test_auth_error_raises(self, mock_config):
        """401 认证错误应抛出 AUTH_FAILED"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("auth", request=MagicMock(), response=mock_response)

        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(VisionLLMError.AUTH_FAILED):
                await safe_call_vision_llm("fake_base64", mock_config)

    @pytest.mark.asyncio
    async def test_rate_limit_raises(self, mock_config):
        """429 限流应抛出 RATE_LIMIT"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("rate limit", request=MagicMock(), response=mock_response)

        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(VisionLLMError.RATE_LIMIT):
                await safe_call_vision_llm("fake_base64", mock_config)

    @pytest.mark.asyncio
    async def test_server_error_raises(self, mock_config):
        """500 服务端错误应抛出 MODEL_ERROR"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response)

        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(VisionLLMError.MODEL_ERROR):
                await safe_call_vision_llm("fake_base64", mock_config)

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self, mock_config):
        """非法 JSON 响应应抛出 INVALID_RESPONSE"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "definitely not json"}}]
        }

        with patch("app.services.vision_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(VisionLLMError.INVALID_RESPONSE):
                await safe_call_vision_llm("fake_base64", mock_config)
```

#### E.2.4 Mock 测试（Qwen Image 客户端重试）

```python
# tests/test_qwen_client.py
"""Qwen Image 客户端重试策略 Mock 测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.services.qwen_client import call_qwen_image_with_retry, QwenImageConfig


@pytest.fixture
def mock_config():
    return QwenImageConfig(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key="sk-test-key",
        model_name="qwen-image-2.0"
    )


class TestQwenImageRetry:

    @pytest.mark.asyncio
    async def test_successful_on_first_try(self, mock_config):
        """首次调用成功应直接返回"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [{"url": "https://example.com/image.png"}]
        }

        with patch("app.services.qwen_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await call_qwen_image_with_retry("fake_base64", "test prompt", mock_config)

        assert "example.com" in result

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, mock_config):
        """429 限流应自动重试"""
        # 前 2 次返回 429，第 3 次成功
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.raise_for_status.side_effect = httpx.HTTPStatusError("rate limit", request=MagicMock(), response=mock_response_429)

        mock_response_ok = MagicMock()
        mock_response_ok.json.return_value = {
            "data": [{"url": "https://example.com/image.png"}]
        }

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.HTTPStatusError("rate limit", request=MagicMock(), response=mock_response_429)
            return mock_response_ok

        with patch("app.services.qwen_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.services.qwen_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await call_qwen_image_with_retry("fake_base64", "test prompt", mock_config)

        assert call_count == 3
        assert mock_sleep.call_count == 2
        assert "example.com" in result

    @pytest.mark.asyncio
    async def test_no_retry_on_timeout(self, mock_config):
        """超时不应重试"""
        with patch("app.services.qwen_client.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(httpx.TimeoutException):
                await call_qwen_image_with_retry("fake_base64", "test prompt", mock_config)

    @pytest.mark.asyncio
    async def test_exhaust_retries_raises(self, mock_config):
        """重试耗尽后应抛出 RuntimeError"""
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status.side_effect = httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response_500)

        with patch("app.services.qwen_client.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(
                side_effect=httpx.HTTPStatusError("server error", request=MagicMock(), response=mock_response_500)
            )
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            with patch("app.services.qwen_client.asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="重试"):
                    await call_qwen_image_with_retry("fake_base64", "test prompt", mock_config)
```

#### E.2.5 集成测试模板

```python
# tests/test_integration.py
"""端到端集成测试模板

运行方式:
  # 需要配置真实 API Key
  export VISION_LLM_API_KEY=sk-xxx
  export VISION_LLM_BASE_URL=https://api.openai.com
  export QWEN_API_KEY=sk-xxx
  pytest tests/test_integration.py -v --tb=short

  # 跳过集成测试（CI 环境）
  pytest tests/ -v -m "not integration"
"""

import json
import pytest
import httpx
import base64
from pathlib import Path

# 标记所有集成测试
pytestmark = pytest.mark.integration


# --- 测试用照片准备 ---

SAMPLE_PHOTO_PATH = Path(__file__).parent / "fixtures" / "sample_photo.jpg"


def get_sample_photo_base64() -> str:
    """读取测试用照片并返回 base64 编码"""
    if not SAMPLE_PHOTO_PATH.exists():
        pytest.skip("测试照片不存在，跳过集成测试")
    with open(SAMPLE_PHOTO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# --- Vision LLM 集成测试 ---

class TestVisionLLMIntegration:

    @pytest.mark.asyncio
    async def test_analyze_real_photo_returns_valid_json(self):
        """真实照片应返回合法的 3 选项 JSON"""
        pytest.skip("需要配置真实 API Key")
        # 实际实现:
        # from app.services.vision_client import safe_call_vision_llm
        # from app.services.vision_parser import parse_vision_response
        # config = VisionLLMConfig(base_url=..., api_key=..., model_name=...)
        # base64_img = get_sample_photo_base64()
        # raw = await safe_call_vision_llm(base64_img, config)
        # options = parse_vision_response(raw)
        # assert len(options) == 3
        # for opt in options:
        #     assert "masterpiece" in opt["prompt"]

    @pytest.mark.asyncio
    async def test_analyze_multiple_styles_are_distinct(self):
        """3 个风格选项应各不相同"""
        pytest.skip("需要配置真实 API Key")
        # 验证 3 个选项的 name 互不相同
        # 验证 3 个选项的 prompt 有明显差异（可简单检查 prompt 之间的编辑距离或关键词差异）

    @pytest.mark.asyncio
    async def test_prompt_quality_check(self):
        """prompt 应包含所有必要的维度描述"""
        pytest.skip("需要配置真实 API Key")
        # 验证每个 prompt 包含以下维度的描述:
        # 构图: composition, shot, framed
        # 光影: lighting, light, shadow
        # 色彩: color, tone, hue
        # 人物: person, figure, character, face, hair
        # 服装: cloth, outfit, wear, costume
        # 场景: scene, background, environment
        # 镜头: camera, lens, angle, view
        # 画质: masterpiece, best quality, ultra-detailed, 8K


# --- Qwen Image 集成测试 ---

class TestQwenImageIntegration:

    @pytest.mark.asyncio
    async def test_generate_real_artwork_returns_image(self):
        """真实调用应返回有效的图片"""
        pytest.skip("需要配置真实 API Key")
        # 实际实现:
        # from app.services.qwen_client import call_qwen_image_with_retry
        # from app.services.qwen_parser import parse_qwen_image_response
        # config = QwenImageConfig(base_url=..., api_key=..., model_name=...)
        # base64_img = get_sample_photo_base64()
        # prompt = "masterpiece, best quality, a cyberpunk portrait..."
        # raw = await call_qwen_image_with_retry(base64_img, prompt, config)
        # image_result = parse_qwen_image_response(raw)
        # assert image_result.startswith("https://") or image_result.startswith("data:image")

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """完整管线: 照片 → Vision LLM → 用户选择 → Qwen Image → 海报"""
        pytest.skip("需要配置真实 API Key")
        # 实际实现:
        # 1. 准备照片
        # 2. 调用 /api/analyze
        # 3. 解析选项，选择第 0 个
        # 4. 调用 /api/generate
        # 5. 验证返回图片有效
```

#### E.2.6 conftest.py 配置

```python
# tests/conftest.py
"""pytest 全局配置"""

import pytest


def pytest_configure(config):
    """注册自定义标记"""
    config.addinivalue_line("markers", "integration: 集成测试（需要真实 API Key）")
    config.addinivalue_line("markers", "unit: 单元测试")


def pytest_collection_modifyitems(config, items):
    """默认跳过集成测试（除非显式指定）"""
    if not config.getoption("-m", default=None):
        skip_integration = pytest.mark.skip(reason="使用 -m integration 运行集成测试")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
```

---

## 附录

### F.1 环境变量清单

```env
# Vision LLM 配置
VISION_LLM_BASE_URL=https://api.openai.com        # OpenAI-compatible API 地址
VISION_LLM_API_KEY=sk-xxxxxxxx                    # API Key
VISION_LLM_MODEL=gpt-4o                           # 模型名称

# Qwen Image 配置
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_API_KEY=sk-xxxxxxxx
QWEN_IMAGE_MODEL=qwen-image-2.0

# 会话配置
SESSION_TTL=1800                                   # 会话有效期（秒）
```

### F.2 依赖版本

```
httpx>=0.27.0
pydantic>=2.0
python-dotenv>=1.0.0
fastapi>=0.110.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

### F.3 文件结构参考

```
app/
  services/
    vision_client.py      # Vision LLM 调用与异常处理
    vision_parser.py      # Vision LLM 响应解析
    qwen_client.py        # Qwen Image 调用与重试
    qwen_parser.py        # Qwen Image 响应解析
    prompt_template.py    # 系统提示词模板（A.5 内容）
    session_cache.py      # 会话缓存管理
  routes/
    analyze.py            # POST /api/analyze
    generate.py           # POST /api/generate
    history.py            # GET /api/history
  models/
    schemas.py            # Pydantic 请求/响应模型

tests/
  conftest.py
  test_vision_parser.py   # Vision 响应解析单元测试
  test_vision_client.py   # Vision 客户端 Mock 测试
  test_qwen_parser.py     # Qwen 响应解析单元测试
  test_qwen_client.py     # Qwen 客户端重试 Mock 测试
  test_integration.py     # 集成测试模板
  fixtures/
    sample_photo.jpg      # 测试用照片
```
