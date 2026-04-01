# Pose Art Generator — 后端规格文档

> 版本：1.0
> 日期：2026-03-28
> 技术栈：Python 3.11+ / FastAPI / Uvicorn / httpx / pydantic / pydantic-settings

---

## A. 项目结构

### A.1 目录结构

```
backend/
├── app/
│   ├── __init__.py                # 包初始化
│   ├── main.py                    # FastAPI 应用入口，挂载路由、启动/关闭事件
│   ├── config.py                  # pydantic-settings 配置加载，定义 Settings 类
│   ├── dependencies.py            # FastAPI Depends 注入（LLM 客户端单例等）
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analyze.py             # POST /api/analyze 路由
│   │   ├── generate.py            # POST /api/generate 路由
│   │   └── history.py             # GET  /api/history 路由
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── analyze.py             # analyze 请求/响应 Pydantic 模型
│   │   ├── generate.py            # generate 请求/响应 Pydantic 模型
│   │   └── history.py             # history 响应 Pydantic 模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_client.py          # OpenAI-compatible LLM 客户端封装
│   │   ├── image_gen_client.py    # Qwen Image 2.0 客户端封装
│   │   ├── analyze_service.py     # 照片分析业务逻辑
│   │   ├── generate_service.py    # 海报生成业务逻辑
│   │   └── history_service.py     # 历史记录读写逻辑
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── system_prompt.py       # Vision LLM 系统提示词模板
│   └── storage/
│       ├── __init__.py
│       └── file_storage.py        # 本地文件系统存储实现
├── data/
│   ├── photos/                    # 用户上传的原始照片
│   └── posters/                   # 生成的海报图片
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest fixtures（测试客户端、mock 等）
│   ├── test_analyze.py            # analyze 接口测试
│   ├── test_generate.py           # generate 接口测试
│   └── test_history.py            # history 接口测试
├── .env                           # 环境变量配置（不入库）
├── .env.example                   # 环境变量示例
├── requirements.txt               # Python 依赖
└── run.py                         # uvicorn 启动脚本
```

### A.2 关键文件职责

| 文件 | 职责 |
|------|------|
| `app/main.py` | 创建 FastAPI 实例，注册路由（`/api/analyze`、`/api/generate`、`/api/history`），配置 CORS 中间件，定义 lifespan 事件 |
| `app/config.py` | 使用 `pydantic-settings` 的 `BaseSettings` 从 `.env` 加载所有配置项，提供全局 `get_settings()` 函数 |
| `app/dependencies.py` | FastAPI 依赖注入：LLM 客户端单例、Storage 单例、Settings 单例 |
| `app/routers/analyze.py` | 接收照片，调用 `analyze_service`，返回风格选项列表 |
| `app/routers/generate.py` | 接收照片 + prompt，调用 `generate_service`，返回海报 URL |
| `app/routers/history.py` | 查询历史记录，支持分页 |
| `app/services/llm_client.py` | 封装 OpenAI-compatible API 调用，支持 Vision（多模态输入），内置超时和重试 |
| `app/services/image_gen_client.py` | 封装 Qwen Image 2.0 API 调用，图生图模式 |
| `app/services/analyze_service.py` | 组装系统提示词 + 用户消息，调用 LLM，解析 JSON 响应 |
| `app/services/generate_service.py` | 组装生图请求，调用 Qwen API，下载并保存海报 |
| `app/services/history_service.py` | 基于本地 JSON 文件的历史记录增删查 |
| `app/storage/file_storage.py` | 封装文件保存逻辑：生成唯一文件名、按日期分目录存储 |
| `app/prompts/system_prompt.py` | 预定义 Vision LLM 系统提示词模板，包含角色设定、风格方向池、输出 JSON schema、提示词写作规范 |
| `run.py` | `uvicorn.run("app.main:app", ...)` 启动脚本 |

### A.3 requirements.txt 依赖

```
# Web Framework
fastapi>=0.110.0
uvicorn[standard]>=0.29.0

# HTTP Client（调用 LLM / Image Gen API）
httpx>=0.27.0

# Data Validation & Settings
pydantic>=2.6.0
pydantic-settings>=2.2.0

# Image Processing
Pillow>=10.2.0

# Utilities
python-multipart>=0.0.9

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx  # 用于 TestClient
```

---

## B. 配置设计

### B.1 .env 配置项清单

```env
# ===== 应用配置 =====
APP_NAME=PoseArtGenerator
APP_VERSION=1.0.0
DEBUG=false
HOST=0.0.0.0
PORT=8000

# ===== Vision LLM 配置（OpenAI-compatible） =====
VISION_LLM_BASE_URL=https://api.openai.com/v1
VISION_LLM_API_KEY=sk-your-vision-llm-api-key
VISION_LLM_MODEL=gpt-4o
VISION_LLM_MAX_TOKENS=2048
VISION_LLM_TIMEOUT=60
VISION_LLM_MAX_RETRIES=3

# ===== Qwen Image 2.0 配置 =====
QWEN_IMAGE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_IMAGE_API_KEY=sk-your-qwen-image-api-key
QWEN_IMAGE_MODEL=qwen-image-2.0
QWEN_IMAGE_TIMEOUT=120
QWEN_IMAGE_MAX_RETRIES=3

# ===== 存储配置 =====
PHOTO_STORAGE_DIR=data/photos
POSTER_STORAGE_DIR=data/posters
HISTORY_FILE=data/history.json
MAX_HISTORY_RECORDS=1000

# ===== CORS 配置 =====
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### B.2 pydantic-settings 加载方式

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl


class Settings(BaseSettings):
    """应用配置，从 .env 文件和环境变量加载"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 应用配置
    app_name: str = "PoseArtGenerator"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # Vision LLM
    vision_llm_base_url: str = "https://api.openai.com/v1"
    vision_llm_api_key: str = ""
    vision_llm_model: str = "gpt-4o"
    vision_llm_max_tokens: int = 2048
    vision_llm_timeout: int = 60
    vision_llm_max_retries: int = 3

    # Qwen Image 2.0
    qwen_image_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_image_api_key: str = ""
    qwen_image_model: str = "qwen-image-2.0"
    qwen_image_timeout: int = 120
    qwen_image_max_retries: int = 3

    # 存储
    photo_storage_dir: str = "data/photos"
    poster_storage_dir: str = "data/posters"
    history_file: str = "data/history.json"
    max_history_records: int = 1000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


def get_settings() -> Settings:
    return Settings()
```

---

## C. API 接口设计

### C.1 公共约定

#### 基础 URL

```
http://localhost:8000
```

#### 公共响应格式

所有接口返回 JSON，遵循统一信封格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

错误响应：

```json
{
  "code": 40001,
  "message": "具体错误描述",
  "data": null
}
```

#### 公共错误码

| 错误码 | HTTP 状态码 | 含义 |
|--------|------------|------|
| 0 | 200 | 成功 |
| 40001 | 400 | 请求参数校验失败 |
| 40002 | 400 | 图片格式不支持（仅接受 JPEG/PNG/WebP） |
| 40003 | 400 | 图片大小超限（最大 10MB） |
| 50001 | 500 | Vision LLM 调用失败 |
| 50002 | 500 | Vision LLM 返回格式异常 |
| 50003 | 500 | Qwen Image 调用失败 |
| 50004 | 500 | 图片生成结果下载失败 |
| 50005 | 500 | 内部服务错误 |

---

### C.2 POST /api/analyze — 照片分析

#### 功能描述

接收用户拍照的 Base64 图片，调用 Vision LLM 分析人物姿态和特征，返回 3 个创意风格选项。

#### 请求体 Schema

```python
# app/schemas/analyze.py
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """分析请求体"""
    image_base64: str = Field(
        ...,
        description="Base64 编码的图片（不含 data:image/xxx;base64, 前缀）",
        min_length=1,
    )
    image_format: str = Field(
        default="jpeg",
        description="图片格式：jpeg / png / webp",
        pattern="^(jpeg|png|webp)$",
    )
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_base64` | string | 是 | Base64 编码图片数据，不含 MIME 前缀 |
| `image_format` | string | 否 | 图片格式，默认 `jpeg`，枚举值：`jpeg`/`png`/`webp` |

#### 响应体 Schema

```python
class StyleOption(BaseModel):
    """单个风格选项"""
    name: str = Field(..., description="风格名称，如 '赛博朋克'")
    brief: str = Field(..., description="给用户看的简略描述（一句话）")
    prompt: str = Field(..., description="给生图模型的详细提示词")


class AnalyzeResponse(BaseModel):
    """分析成功时的 data 部分"""
    options: list[StyleOption] = Field(
        ...,
        description="3 个风格选项",
        min_length=1,
        max_length=3,
    )
```

成功响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "options": [
      {
        "name": "赛博朋克霓虹",
        "brief": "未来都市中霓虹灯映照的科技感人像",
        "prompt": "A cyberpunk portrait of a person standing confidently in a neon-lit futuristic city street, rain-soaked ground reflecting pink and cyan neon signs, wearing a dark techwear jacket with glowing circuit patterns, volumetric fog, cinematic lighting, dramatic angle from below, ultra-detailed, 8K"
      },
      {
        "name": "水墨写意",
        "brief": "东方水墨画风格的飘逸人像",
        "prompt": "Traditional Chinese ink wash painting of a person in flowing robes, standing on a misty mountain peak, splashed ink technique with varying ink density, minimalist background with pine trees, calligraphic brush strokes, rice paper texture, monochrome with subtle color accents"
      },
      {
        "name": "波普艺术",
        "brief": "Andy Warhol 风格的鲜艳色块人像",
        "prompt": "Pop art portrait in the style of Andy Warhol, bold flat color blocks in hot pink electric blue and sunny yellow, halftone dot pattern overlay, comic book style outlines, high contrast, four-panel repeated composition, screen print aesthetic"
      }
    ]
  }
}
```

#### 调用 Vision LLM 流程

```
1. 校验请求参数（image_base64 非空、image_format 合法）
2. 解码 Base64，校验图片尺寸 <= 10MB，格式与声明一致
3. 构造 OpenAI-compatible chat completions 请求：
   - model: settings.vision_llm_model
   - messages:
     - role: "system", content: system_prompt（从 app/prompts/system_prompt.py 加载）
     - role: "user", content:
       - type: "image_url", image_url: { url: "data:image/{format};base64,{base64_data}" }
       - type: "text", text: "请分析照片中的人物，生成 3 个创意风格选项"
   - max_tokens: settings.vision_llm_max_tokens
   - temperature: 0.7
4. 发送请求，超时时间 settings.vision_llm_timeout，失败重试 settings.vision_llm_max_retries 次
5. 解析 LLM 返回的 content，提取 JSON（处理 markdown 代码块包裹的情况）
6. 校验 JSON 结构符合 StyleOption 列表格式，至少 1 个选项
7. 返回响应
```

#### 错误场景与错误码

| 场景 | 错误码 | HTTP 状态码 |
|------|--------|------------|
| `image_base64` 为空 | 40001 | 400 |
| `image_format` 不在枚举中 | 40001 | 400 |
| Base64 解码失败 | 40001 | 400 |
| 图片大小超过 10MB | 40003 | 400 |
| 图片格式与声明不一致 | 40002 | 400 |
| LLM API 调用超时/网络错误 | 50001 | 500 |
| LLM 返回内容非有效 JSON | 50002 | 500 |
| LLM 返回 JSON 结构不符 | 50002 | 500 |

---

### C.3 POST /api/generate — 海报生成

#### 功能描述

接收用户照片（Base64）和选中的详细 prompt，调用 Qwen Image 2.0 图生图模式生成海报，保存并返回访问 URL。

#### 请求体 Schema

```python
# app/schemas/generate.py
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """生成请求体"""
    image_base64: str = Field(
        ...,
        description="Base64 编码的原始照片",
        min_length=1,
    )
    image_format: str = Field(
        default="jpeg",
        description="图片格式：jpeg / png / webp",
        pattern="^(jpeg|png|webp)$",
    )
    prompt: str = Field(
        ...,
        description="选中的详细生图提示词",
        min_length=1,
        max_length=2000,
    )
    style_name: str = Field(
        ...,
        description="选中的风格名称，用于历史记录",
        min_length=1,
    )
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_base64` | string | 是 | 原始照片 Base64 |
| `image_format` | string | 否 | 图片格式，默认 `jpeg` |
| `prompt` | string | 是 | 选中的详细生图提示词，1-2000 字符 |
| `style_name` | string | 是 | 选中的风格名称，用于历史记录 |

#### 响应体 Schema

```python
class GenerateResponse(BaseModel):
    """生成成功时的 data 部分"""
    poster_url: str = Field(..., description="海报图片的访问 URL")
    thumbnail_url: str = Field(..., description="缩略图访问 URL")
    history_id: str = Field(..., description="历史记录 ID（UUID）")
```

成功响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "poster_url": "/data/posters/2026-03-28/abc123def456.png",
    "thumbnail_url": "/data/posters/2026-03-28/abc123def456_thumb.png",
    "history_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### 调用 Qwen Image 2.0 流程

```
1. 校验请求参数
2. 解码 Base64，校验图片大小和格式（同 analyze 接口）
3. 将原图保存到 data/photos/{date}/{uuid}.{ext}
4. 构造 Qwen Image 2.0 API 请求（OpenAI-compatible images/edits 或 images/generations）：
   - model: settings.qwen_image_model
   - 输入图片：用户上传的原图
   - prompt: 用户选中的详细 prompt
   - size: "1024x1024"（默认）
   - n: 1
5. 发送请求，超时时间 settings.qwen_image_timeout，失败重试 settings.qwen_image_max_retries 次
6. 从响应中获取生成的图片 URL 或 Base64 数据
7. 下载/解码生成图片，保存到 data/posters/{date}/{uuid}.png
8. 生成缩略图（256x256），保存到 data/posters/{date}/{uuid}_thumb.png
9. 写入历史记录到 data/history.json
10. 返回海报 URL、缩略图 URL 和历史记录 ID
```

#### Qwen Image 2.0 API 调用示例

```python
# OpenAI-compatible 格式
async with httpx.AsyncClient(timeout=settings.qwen_image_timeout) as client:
    response = await client.post(
        f"{settings.qwen_image_base_url}/images/generations",
        headers={"Authorization": f"Bearer {settings.qwen_image_api_key}"},
        json={
            "model": settings.qwen_image_model,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            # 图生图参数（视 API 实际支持情况）
            "image": f"data:image/{image_format};base64,{image_base64}",
        },
    )
```

#### 错误场景与错误码

| 场景 | 错误码 | HTTP 状态码 |
|------|--------|------------|
| `image_base64` 为空 | 40001 | 400 |
| `prompt` 为空或超长 | 40001 | 400 |
| `style_name` 为空 | 40001 | 400 |
| 图片大小超过 10MB | 40003 | 400 |
| Qwen Image API 调用超时/网络错误 | 50003 | 500 |
| 生成结果下载/解码失败 | 50004 | 500 |
| 文件保存失败 | 50005 | 500 |

---

### C.4 GET /api/history — 历史记录

#### 功能描述

分页查询海报生成历史记录，按创建时间倒序排列。

#### 请求参数（Query Parameters）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | int | 否 | 1 | 页码，从 1 开始，最小值 1 |
| `page_size` | int | 否 | 20 | 每页条数，范围 1-100 |

#### 响应体 Schema

```python
# app/schemas/history.py
from pydantic import BaseModel, Field
from datetime import datetime


class HistoryItem(BaseModel):
    """单条历史记录"""
    id: str = Field(..., description="记录唯一 ID（UUID）")
    style_name: str = Field(..., description="使用的风格名称")
    prompt: str = Field(..., description="使用的生图提示词")
    poster_url: str = Field(..., description="海报图片 URL")
    thumbnail_url: str = Field(..., description="缩略图 URL")
    created_at: str = Field(..., description="创建时间，ISO 8601 格式")


class HistoryResponse(BaseModel):
    """历史记录成功时的 data 部分"""
    items: list[HistoryItem] = Field(..., description="当前页记录列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")
```

成功响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "style_name": "赛博朋克霓虹",
        "prompt": "A cyberpunk portrait of a person...",
        "poster_url": "/data/posters/2026-03-28/abc123def456.png",
        "thumbnail_url": "/data/posters/2026-03-28/abc123def456_thumb.png",
        "created_at": "2026-03-28T14:30:00+08:00"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

#### 历史记录存储格式（data/history.json）

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "style_name": "赛博朋克霓虹",
    "prompt": "A cyberpunk portrait of a person...",
    "poster_url": "/data/posters/2026-03-28/abc123def456.png",
    "thumbnail_url": "/data/posters/2026-03-28/abc123def456_thumb.png",
    "photo_url": "/data/photos/2026-03-28/def789ghi012.jpeg",
    "created_at": "2026-03-28T14:30:00+08:00"
  }
]
```

---

## D. LLM 客户端设计

### D.1 OpenAI-compatible 客户端封装

```python
# app/services/llm_client.py
import httpx
import json
import re
from app.config import Settings


class LLMClient:
    """OpenAI-compatible API 客户端，支持 Vision 多模态调用"""

    def __init__(self, settings: Settings):
        self.base_url = settings.vision_llm_base_url.rstrip("/")
        self.api_key = settings.vision_llm_api_key
        self.model = settings.vision_llm_model
        self.max_tokens = settings.vision_llm_max_tokens
        self.timeout = settings.vision_llm_timeout
        self.max_retries = settings.vision_llm_max_retries

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def chat_with_vision(
        self,
        system_prompt: str,
        image_base64: str,
        image_format: str,
        user_text: str,
        temperature: float = 0.7,
    ) -> str:
        """
        调用 Vision LLM，发送图文消息。

        Args:
            system_prompt: 系统提示词
            image_base64: 图片 Base64 数据
            image_format: 图片格式（jpeg/png/webp）
            user_text: 用户文本消息
            temperature: 采样温度

        Returns:
            LLM 返回的文本内容（choices[0].message.content）

        Raises:
            LLMTimeoutError: 超时且重试耗尽
            LLMApiError: API 返回非 200 状态码
            LLMResponseError: 响应结构异常
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{image_base64}"
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                },
            ],
            "max_tokens": self.max_tokens,
            "temperature": temperature,
        }

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self._build_url("/chat/completions"),
                        headers=self._build_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except httpx.TimeoutException as e:
                last_exception = e
                continue
            except httpx.HTTPStatusError as e:
                last_exception = e
                # 4xx 错误不重试
                if 400 <= e.response.status_code < 500:
                    raise LLMApiError(
                        f"LLM API 返回错误: {e.response.status_code} {e.response.text}"
                    ) from e
                continue
            except (KeyError, IndexError) as e:
                raise LLMResponseError(
                    f"LLM 响应结构异常: {e}"
                ) from e

        raise LLMTimeoutError(
            f"LLM 调用超时，已重试 {self.max_retries} 次: {last_exception}"
        )

    @staticmethod
    def extract_json_from_content(content: str) -> dict:
        """
        从 LLM 输出中提取 JSON 对象。
        兼容以下情况：
        1. 纯 JSON 字符串
        2. Markdown 代码块包裹的 JSON：```json ... ```
        """
        content = content.strip()

        # 尝试从 markdown 代码块中提取
        pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = match.group(1).strip()

        return json.loads(content)


class LLMTimeoutError(Exception):
    """LLM 调用超时"""
    pass


class LLMApiError(Exception):
    """LLM API 返回错误"""
    pass


class LLMResponseError(Exception):
    """LLM 响应结构异常"""
    pass
```

### D.2 关键设计决策

| 决策点 | 方案 |
|--------|------|
| HTTP 客户端 | 使用 `httpx.AsyncClient`，支持 async/await |
| 超时策略 | 整体请求超时（`timeout` 参数），默认 60 秒 |
| 重试策略 | 指数退避重试，仅对 5xx 服务端错误和超时重试，4xx 客户端错误立即抛出 |
| 重试次数 | 可配置，默认 3 次 |
| JSON 提取 | 兼容纯 JSON 和 Markdown 代码块两种格式 |
| 错误处理 | 自定义异常类 `LLMTimeoutError`、`LLMApiError`、`LLMResponseError`，由路由层捕获并转换为错误响应 |

### D.3 Qwen Image 2.0 客户端封装

```python
# app/services/image_gen_client.py
import httpx
import base64
from app.config import Settings


class ImageGenClient:
    """Qwen Image 2.0 API 客户端"""

    def __init__(self, settings: Settings):
        self.base_url = settings.qwen_image_base_url.rstrip("/")
        self.api_key = settings.qwen_image_api_key
        self.model = settings.qwen_image_model
        self.timeout = settings.qwen_image_timeout
        self.max_retries = settings.qwen_image_max_retries

    async def generate(
        self,
        prompt: str,
        image_base64: str,
        image_format: str = "jpeg",
        size: str = "1024x1024",
    ) -> str:
        """
        图生图模式生成海报。

        Args:
            prompt: 生图提示词
            image_base64: 参考图片 Base64
            image_format: 参考图片格式
            size: 生成图片尺寸

        Returns:
            生成图片的 Base64 数据

        Raises:
            ImageGenTimeoutError: 超时且重试耗尽
            ImageGenApiError: API 返回非 200
            ImageGenResponseError: 响应结构异常
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "image": f"data:image/{image_format};base64,{image_base64}",
        }

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/images/generations",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.api_key}",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    # 根据 API 实际返回格式提取图片
                    # 可能是 URL 或 Base64
                    image_data = data["data"][0]
                    if "b64_json" in image_data:
                        return image_data["b64_json"]
                    elif "url" in image_data:
                        # 下载 URL 图片并转为 Base64
                        img_resp = await client.get(image_data["url"])
                        img_resp.raise_for_status()
                        return base64.b64encode(img_resp.content).decode("utf-8")
                    else:
                        raise ImageGenResponseError("API 响应中未包含图片数据")
            except httpx.TimeoutException as e:
                last_exception = e
                continue
            except httpx.HTTPStatusError as e:
                last_exception = e
                if 400 <= e.response.status_code < 500:
                    raise ImageGenApiError(
                        f"Image Gen API 错误: {e.response.status_code} {e.response.text}"
                    ) from e
                continue

        raise ImageGenTimeoutError(
            f"Image Gen 超时，已重试 {self.max_retries} 次: {last_exception}"
        )


class ImageGenTimeoutError(Exception):
    pass


class ImageGenApiError(Exception):
    pass


class ImageGenResponseError(Exception):
    pass
```

---

## E. 图片存储设计

### E.1 目录结构

```
data/
├── photos/                          # 用户上传的原始照片
│   ├── 2026-03-28/                  # 按日期分目录
│   │   ├── a1b2c3d4e5f6.jpeg
│   │   └── f6e5d4c3b2a1.png
│   └── 2026-03-29/
│       └── ...
├── posters/                         # 生成的海报
│   ├── 2026-03-28/
│   │   ├── a1b2c3d4e5f6.png        # 全尺寸海报
│   │   ├── a1b2c3d4e5f6_thumb.png  # 缩略图（256x256）
│   │   └── ...
│   └── 2026-03-29/
│       └── ...
└── history.json                     # 历史记录（JSON 数组）
```

### E.2 文件命名规则

- **命名格式**：`{uuid}.{ext}`
- **UUID 版本**：UUID4（随机生成）
- **目录层级**：按创建日期（`YYYY-MM-DD`）分目录，避免单目录文件过多
- **海报与原图关联**：海报和原图共用同一个 UUID，确保可追溯

### E.3 存储实现

```python
# app/storage/file_storage.py
import base64
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import io


class FileStorage:
    """本地文件系统存储"""

    def __init__(self, photo_dir: str, poster_dir: str):
        self.photo_dir = Path(photo_dir)
        self.poster_dir = Path(poster_dir)

    def _ensure_date_dir(self, base_dir: Path, date_str: str) -> Path:
        date_path = base_dir / date_str
        date_path.mkdir(parents=True, exist_ok=True)
        return date_path

    def _today_str(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def save_photo(self, image_base64: str, image_format: str) -> dict:
        """
        保存原始照片。

        Returns:
            {"file_path": 相对路径, "url": 访问 URL, "uuid": 文件 UUID}
        """
        file_uuid = uuid.uuid4().hex
        date_str = self._today_str()
        ext = image_format
        if ext == "jpeg":
            ext = "jpg"

        date_dir = self._ensure_date_dir(self.photo_dir, date_str)
        file_name = f"{file_uuid}.{ext}"
        file_path = date_dir / file_name

        image_data = base64.b64decode(image_base64)
        file_path.write_bytes(image_data)

        return {
            "file_path": str(file_path),
            "url": f"/data/photos/{date_str}/{file_name}",
            "uuid": file_uuid,
            "date": date_str,
        }

    def save_poster(
        self, image_base64: str, uuid: str, date_str: str
    ) -> dict:
        """
        保存生成的海报及缩略图。

        Returns:
            {"poster_url": ..., "thumbnail_url": ...}
        """
        date_dir = self._ensure_date_dir(self.poster_dir, date_str)

        # 保存全尺寸海报
        poster_name = f"{uuid}.png"
        poster_path = date_dir / poster_name
        image_data = base64.b64decode(image_base64)
        poster_path.write_bytes(image_data)

        # 生成并保存缩略图
        thumb_name = f"{uuid}_thumb.png"
        thumb_path = date_dir / thumb_name
        img = Image.open(io.BytesIO(image_data))
        img.thumbnail((256, 256))
        img.save(thumb_path, "PNG")

        return {
            "poster_url": f"/data/posters/{date_str}/{poster_name}",
            "thumbnail_url": f"/data/posters/{date_str}/{thumb_name}",
        }
```

### E.4 静态文件挂载

在 `main.py` 中挂载静态文件服务：

```python
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 挂载 data 目录为静态文件
app.mount("/data", StaticFiles(directory="data"), name="data")
```

---

## F. 验收标准

### F.1 接口 curl 测试命令

#### F.1.1 POST /api/analyze

```bash
# 准备：将图片转为 base64（去掉前缀）
IMAGE_BASE64=$(base64 -w 0 test_photo.jpg)

# 正常请求
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"${IMAGE_BASE64}\", \"image_format\": \"jpeg\"}"

# 预期：HTTP 200，返回 {"code": 0, "data": {"options": [...]}}
# options 中至少有 1 个选项，最多 3 个，每个选项包含 name、brief、prompt
```

```bash
# 异常：空图片
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "", "image_format": "jpeg"}'

# 预期：HTTP 422 或 400，返回错误码 40001
```

```bash
# 异常：不支持格式
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"${IMAGE_BASE64}\", \"image_format\": \"bmp\"}"

# 预期：HTTP 422 或 400，返回错误码 40001
```

#### F.1.2 POST /api/generate

```bash
# 准备
IMAGE_BASE64=$(base64 -w 0 test_photo.jpg)

# 正常请求
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"image_base64\": \"${IMAGE_BASE64}\",
    \"image_format\": \"jpeg\",
    \"prompt\": \"A cyberpunk portrait of a person standing confidently...\",
    \"style_name\": \"赛博朋克霓虹\"
  }"

# 预期：HTTP 200，返回 {"code": 0, "data": {"poster_url": "/data/posters/...", "thumbnail_url": "...", "history_id": "..."}}
# 可通过 poster_url 访问生成的海报图片
```

```bash
# 验证海报图片可访问
curl -I http://localhost:8000/data/posters/2026-03-28/xxx.png

# 预期：HTTP 200，Content-Type: image/png
```

```bash
# 异常：prompt 为空
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"${IMAGE_BASE64}\", \"image_format\": \"jpeg\", \"prompt\": \"\", \"style_name\": \"test\"}"

# 预期：HTTP 422 或 400，返回错误码 40001
```

#### F.1.3 GET /api/history

```bash
# 默认分页（第 1 页，每页 20 条）
curl http://localhost:8000/api/history

# 预期：HTTP 200，返回 {"code": 0, "data": {"items": [...], "total": N, "page": 1, "page_size": 20, "total_pages": M}}
```

```bash
# 指定分页参数
curl "http://localhost:8000/api/history?page=2&page_size=5"

# 预期：HTTP 200，返回第 2 页数据，每页 5 条
```

```bash
# 边界：超出总页数
curl "http://localhost:8000/api/history?page=9999"

# 预期：HTTP 200，返回 {"items": [], "total": N, "page": 9999, ...}
```

---

### F.2 pytest 测试框架

#### F.2.1 conftest.py

```python
# tests/conftest.py
import pytest
import base64
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image


@pytest.fixture
def sample_image_base64() -> str:
    """生成测试用小图片的 Base64"""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@pytest.fixture
def sample_image_base64_large() -> str:
    """生成接近 10MB 的大图片 Base64（用于大小校验测试）"""
    # 实际测试中可 mock 大小校验逻辑
    return base64.b64encode(b"fake_large_data").decode("utf-8")


@pytest.fixture
def mock_llm_response() -> dict:
    """Vision LLM 成功响应 mock"""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "options": [
                            {
                                "name": "测试风格A",
                                "brief": "测试描述A",
                                "prompt": "Test prompt A for image generation",
                            },
                            {
                                "name": "测试风格B",
                                "brief": "测试描述B",
                                "prompt": "Test prompt B for image generation",
                            },
                            {
                                "name": "测试风格C",
                                "brief": "测试描述C",
                                "prompt": "Test prompt C for image generation",
                            },
                        ]
                    })
                }
            }
        ]
    }


@pytest.fixture
def mock_image_gen_response() -> dict:
    """Qwen Image 生成成功响应 mock"""
    # 生成小图片 Base64 作为 mock 返回
    img = Image.new("RGB", (64, 64), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "data": [
            {"b64_json": b64_data}
        ]
    }
```

#### F.2.2 测试用例清单

##### test_analyze.py

```python
# tests/test_analyze.py

class TestAnalyzeEndpoint:
    """POST /api/analyze 测试"""

    def test_analyze_success(self, client, sample_image_base64, mock_llm_response):
        """
        正常流程：发送有效图片，返回 3 个风格选项
        - Mock LLM 返回合法 JSON
        - 验证 code == 0
        - 验证 data.options 长度为 3
        - 验证每个选项包含 name、brief、prompt 字段
        """

    def test_analyze_empty_image(self, client):
        """
        异常流程：image_base64 为空
        - 验证返回 HTTP 400 或 422
        - 验证错误码为 40001
        """

    def test_analyze_invalid_format(self, client, sample_image_base64):
        """
        异常流程：image_format 不在枚举中
        - 验证返回 HTTP 400 或 422
        - 验证错误码为 40001
        """

    def test_analyze_invalid_base64(self, client):
        """
        异常流程：image_base64 不是有效 Base64
        - 验证返回 HTTP 400
        - 验证错误码为 40001
        """

    def test_analyze_llm_timeout(self, client, sample_image_base64):
        """
        异常流程：LLM 调用超时
        - Mock LLM 抛出超时异常
        - 验证返回 HTTP 500
        - 验证错误码为 50001
        """

    def test_analyze_llm_invalid_json(self, client, sample_image_base64):
        """
        异常流程：LLM 返回非 JSON 内容
        - Mock LLM 返回纯文本
        - 验证返回 HTTP 500
        - 验证错误码为 50002
        """

    def test_analyze_llm_json_with_code_block(self, client, sample_image_base64):
        """
        边界情况：LLM 返回 markdown 代码块包裹的 JSON
        - Mock LLM 返回 "```json\n{...}\n```"
        - 验证正常解析，code == 0
        """

    def test_analyze_missing_required_field(self, client):
        """
        异常流程：缺少必填字段 image_base64
        - 验证返回 HTTP 422
        """
```

##### test_generate.py

```python
# tests/test_generate.py

class TestGenerateEndpoint:
    """POST /api/generate 测试"""

    def test_generate_success(self, client, sample_image_base64, mock_image_gen_response):
        """
        正常流程：发送图片 + prompt，生成海报
        - Mock Qwen Image API 返回图片数据
        - 验证 code == 0
        - 验证 data.poster_url 以 /data/posters/ 开头
        - 验证 data.thumbnail_url 以 _thumb.png 结尾
        - 验证 data.history_id 为有效 UUID 格式
        - 验证海报文件已保存到磁盘
        - 验证缩略图文件已保存到磁盘
        - 验证历史记录已写入
        """

    def test_generate_empty_prompt(self, client, sample_image_base64):
        """
        异常流程：prompt 为空
        - 验证返回 HTTP 400 或 422
        - 验证错误码为 40001
        """

    def test_generate_prompt_too_long(self, client, sample_image_base64):
        """
        异常流程：prompt 超过 2000 字符
        - 验证返回 HTTP 400 或 422
        - 验证错误码为 40001
        """

    def test_generate_empty_style_name(self, client, sample_image_base64):
        """
        异常流程：style_name 为空
        - 验证返回 HTTP 400 或 422
        - 验证错误码为 40001
        """

    def test_generate_image_gen_timeout(self, client, sample_image_base64):
        """
        异常流程：Qwen Image API 调用超时
        - Mock API 抛出超时异常
        - 验证返回 HTTP 500
        - 验证错误码为 50003
        """

    def test_generate_creates_history(self, client, sample_image_base64, mock_image_gen_response):
        """
        验证：生成成功后历史记录正确写入
        - 调用 generate 后查询 GET /api/history
        - 验证新记录出现在列表中
        - 验证字段完整（id、style_name、prompt、poster_url、thumbnail_url、created_at）
        """
```

##### test_history.py

```python
# tests/test_history.py

class TestHistoryEndpoint:
    """GET /api/history 测试"""

    def test_history_empty(self, client):
        """
        空列表：无历史记录
        - 验证 code == 0
        - 验证 data.items 为空列表
        - 验证 data.total == 0
        """

    def test_history_default_pagination(self, client, sample_image_base64, mock_image_gen_response):
        """
        默认分页：不传参数
        - 先调用 generate 创建若干条记录
        - 调用 history，不传 page/page_size
        - 验证 page == 1，page_size == 20
        """

    def test_history_custom_pagination(self, client):
        """
        自定义分页
        - 请求 page=2&page_size=5
        - 验证返回第 2 页，每页 5 条
        - 验证 total_pages 计算正确
        """

    def test_history_page_beyond_total(self, client):
        """
        超出总页数
        - 请求 page=9999
        - 验证 items 为空列表
        - 验证 total 和 total_pages 仍正确
        """

    def test_history_order_descending(self, client):
        """
        排序验证
        - 创建多条记录
        - 验证按 created_at 倒序排列（最新在前）
        """

    def test_history_invalid_page_param(self, client):
        """
        异常：page 参数非正整数
        - 请求 page=0 或 page=-1
        - 验证返回 HTTP 422
        """

    def test_history_page_size_exceeds_limit(self, client):
        """
        异常：page_size 超过 100
        - 请求 page_size=200
        - 验证返回 HTTP 422
        """
```

#### F.2.3 运行测试

```bash
# 运行所有测试
cd backend && python -m pytest tests/ -v

# 运行单个测试文件
cd backend && python -m pytest tests/test_analyze.py -v

# 运行指定测试用例
cd backend && python -m pytest tests/test_analyze.py::TestAnalyzeEndpoint::test_analyze_success -v

# 显示覆盖率
cd backend && python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

### F.3 通过标准

| 标准 | 要求 |
|------|------|
| **测试通过率** | 全部测试用例 100% 通过（0 failures, 0 errors） |
| **接口可用性** | 所有 3 个接口（analyze、generate、history）可通过 curl 正常访问并返回预期结果 |
| **错误处理** | 所有异常场景均返回正确的错误码和 HTTP 状态码，不暴露内部堆栈信息 |
| **图片保存** | generate 成功后，海报和缩略图文件存在于预期路径，可通过 URL 访问 |
| **历史记录** | generate 成功后，history 接口可查询到对应记录，分页参数正确 |
| **代码质量** | `flake8` / `ruff` lint 零错误；类型注解覆盖所有公共函数 |
| **启动验证** | `python run.py` 可正常启动，Uvicorn 监听在配置的 HOST:PORT，访问 `/docs` 可看到 Swagger UI |

### F.4 错误场景覆盖矩阵

| 编号 | 接口 | 场景 | 预期行为 |
|------|------|------|----------|
| E01 | analyze | image_base64 为空 | 返回 40001 |
| E02 | analyze | image_base64 非法 Base64 | 返回 40001 |
| E03 | analyze | image_format 不合法 | 返回 40001 |
| E04 | analyze | 图片超过 10MB | 返回 40003 |
| E05 | analyze | LLM API 网络超时 | 返回 50001 |
| E06 | analyze | LLM API 返回 4xx | 返回 50001 |
| E07 | analyze | LLM 返回非 JSON | 返回 50002 |
| E08 | analyze | LLM JSON 结构不符 | 返回 50002 |
| E09 | analyze | LLM 返回 markdown 代码块包裹的 JSON | 正常解析返回 0 |
| E10 | generate | prompt 为空 | 返回 40001 |
| E11 | generate | prompt 超 2000 字符 | 返回 40001 |
| E12 | generate | style_name 为空 | 返回 40001 |
| E13 | generate | 图片超过 10MB | 返回 40003 |
| E14 | generate | Qwen API 网络超时 | 返回 50003 |
| E15 | generate | Qwen API 返回 4xx | 返回 50003 |
| E16 | generate | 生成结果下载失败 | 返回 50004 |
| E17 | history | page 为 0 或负数 | 返回 422 |
| E18 | history | page_size 超过 100 | 返回 422 |
| E19 | history | 请求超出总页数 | 返回空列表，total 正确 |
| E20 | history | 无数据时查询 | 返回空列表，total == 0 |
