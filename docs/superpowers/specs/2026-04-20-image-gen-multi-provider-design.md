# 图像生成多 Provider 适配设计

> 日期: 2026-04-20
> 状态: Draft

## 1. 目标

将图像生成客户端从 DashScope 单一绑定改为策略模式，支持通过 `.env` 配置切换 DashScope / OpenRouter 后端。保持上层调用代码零改动。

## 2. 约束

- TDD 开发：先写测试，再写实现
- 每个模块独立验收后再进入下一个
- 最终通过真实 API 集成测试验收
- 现有测试不能 break
- `comic_node.py`、`comic.py` 路由层零改动

## 2.1 范围限定

- `generate_from_text`（文生图）：两个 provider 都实现，这是漫画生成的核心路径
- `generate`（图生图）：仅 DashScope 支持。OpenRouter 的 `generate` 方法抛出 `ImageGenApiError("OpenRouter does not support image-to-image generation")`。当前漫画流程只用 `generate_from_text`，不受影响

## 3. 架构

### 3.1 文件结构

```
backend/app/services/
├── image_gen/                        # 新模块
│   ├── __init__.py                   # 公开 API + 异常 re-export
│   ├── base.py                       # Protocol + ImageSize + 共享工具
│   ├── dashscope_provider.py         # DashScope 实现（从现有代码提取）
│   ├── openrouter_provider.py        # OpenRouter 实现（新增）
│   └── factory.py                    # create_provider() 工厂函数
├── image_gen_client.py               # 向后兼容薄包装（委托给 image_gen/）
```

### 3.2 依赖关系

```
comic_node.py
  └── image_gen_client.py (ImageGenClient — 向后兼容外壳)
        └── image_gen/__init__.py (create_image_gen_client)
              └── factory.py
                    ├── dashscope_provider.py → base.py
                    └── openrouter_provider.py → base.py
```

上层代码（`comic_node.py`、`routers/comic.py`）继续 import `ImageGenClient`、`ImageGenApiError`、`ImageGenTimeoutError`，路径不变。

### 3.3 核心接口

```python
# base.py
@dataclass(frozen=True)
class ImageSize:
    width: int
    height: int

class ImageGenProvider(Protocol):
    async def generate_from_text(self, prompt: str, size: ImageSize) -> str: ...
    async def generate(self, prompt: str, image_base64: str, size: ImageSize) -> str: ...
```

返回值统一为 `data:image/...;base64,...` 格式字符串。

### 3.4 尺寸映射

| ImageSize | DashScope 格式 | OpenRouter 格式 |
|-----------|---------------|----------------|
| 1536×2688 (9:16) | `"1536*2688"` | `aspect_ratio: "9:16", image_size: "2K"` |
| 1024×1024 (1:1) | `"1024*1024"` | `aspect_ratio: "1:1"` |

各 provider 内部实现 `_convert_size(size: ImageSize)` 方法。

### 3.5 OpenRouter 请求/响应格式

请求:
```json
{
  "model": "google/gemini-2.5-flash-image",
  "messages": [{"role": "user", "content": "prompt text"}],
  "modalities": ["image", "text"],
  "image_config": {"aspect_ratio": "9:16", "image_size": "2K"}
}
```

响应:
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "...",
      "images": [{
        "type": "image_url",
        "image_url": {"url": "data:image/png;base64,iVBOR..."}
      }]
    }
  }]
}
```

关键差异：OpenRouter 直接返回 base64 data URL，不需要额外下载步骤。

## 4. 配置变更

`config.py` 新增字段:

```python
# 图像生成 Provider 选择
image_gen_provider: str = "dashscope"   # "dashscope" | "openrouter"

# OpenRouter 图像生成
openrouter_image_apikey: str = ""
openrouter_image_base_url: str = "https://openrouter.ai/api/v1"
openrouter_image_model: str = "google/gemini-2.5-flash-image"
openrouter_image_timeout: int = 120
openrouter_image_max_retries: int = 3
```

现有 `qwen_image_*` 字段保持不变。

`.env.example` 新增:
```env
# Image generation provider: "dashscope" or "openrouter"
IMAGE_GEN_PROVIDER=dashscope

# OpenRouter image generation (when IMAGE_GEN_PROVIDER=openrouter)
OPENROUTER_IMAGE_APIKEY=your-openrouter-api-key
OPENROUTER_IMAGE_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_IMAGE_MODEL=google/gemini-2.5-flash-image
```

## 5. 向后兼容层

`image_gen_client.py` 改为薄包装:

```python
from app.services.image_gen import (
    ImageGenApiError,
    ImageGenTimeoutError,
    create_image_gen_client,
)
from app.services.image_gen.base import ImageSize

class ImageGenClient:
    """向后兼容包装 — 委托给 provider 实现。"""
    def __init__(self, settings: Settings):
        self._provider = create_image_gen_client(settings)

    async def generate_from_text(self, prompt: str, size: str = "1536*2688") -> str:
        w, h = size.split("*")
        return await self._provider.generate_from_text(prompt, ImageSize(int(w), int(h)))

    async def generate(self, prompt: str, image_base64: str,
                       image_format: str = "jpeg", size: str = "1024*1024") -> str:
        w, h = size.split("*")
        return await self._provider.generate(prompt, image_base64, ImageSize(int(w), int(h)))
```

这样 `comic_node.py` 中 `ImageGenClient(settings).generate_from_text(prompt, size="1536*2688")` 完全不变。

## 6. 重试与异常

### 共享逻辑（base.py）

```python
async def retry_with_backoff(
    fn: Callable, max_retries: int, timeout: float, logger: Logger
) -> Any:
    """统一重试逻辑：5xx/连接错误重试，4xx/超时不重试。"""
```

两个 provider 都调用此函数，避免重复实现重试循环。

### 异常类（base.py）

```python
class ImageGenApiError(Exception): ...
class ImageGenTimeoutError(Exception): ...
```

从 `image_gen/__init__.py` re-export，`image_gen_client.py` 也 re-export，保持所有现有 import 路径有效。

## 7. TDD 开发顺序与验收标准

### Phase 1: base.py — 基础设施

测试文件: `tests/backend/unit/test_image_gen_base.py`

| 测试 | 验收标准 |
|------|---------|
| `test_image_size_creation` | ImageSize(1536, 2688) 正确创建，frozen 不可变 |
| `test_image_size_aspect_ratio` | aspect_ratio 属性返回正确比例字符串 |
| `test_retry_success_first_attempt` | 首次成功直接返回 |
| `test_retry_5xx_then_success` | 5xx 后重试成功 |
| `test_retry_4xx_no_retry` | 4xx 直接抛 ImageGenApiError |
| `test_retry_timeout_no_retry` | 超时直接抛 ImageGenTimeoutError |
| `test_retry_exhausted` | 重试耗尽抛 ImageGenApiError |

### Phase 2: dashscope_provider.py — 提取现有逻辑

测试文件: `tests/backend/unit/test_dashscope_provider.py`

| 测试 | 验收标准 |
|------|---------|
| `test_convert_size` | ImageSize(1536,2688) → "1536*2688" |
| `test_build_text_payload` | 构建正确的 DashScope 请求体 |
| `test_build_image_payload` | 图生图请求体包含 image + text content |
| `test_parse_sync_response` | 解析 choices 格式响应 |
| `test_parse_async_response` | 解析 results 格式响应 |
| `test_parse_invalid_raises` | 无效响应抛 ImageGenApiError |
| `test_generate_from_text_success` | mock httpx，完整流程返回 base64 |
| `test_generate_from_text_downloads_url` | 验证 URL 被下载并转为 base64 |

### Phase 3: openrouter_provider.py — 新增实现

测试文件: `tests/backend/unit/test_openrouter_provider.py`

| 测试 | 验收标准 |
|------|---------|
| `test_convert_size_9_16` | ImageSize(1536,2688) → aspect_ratio="9:16", image_size="2K" |
| `test_convert_size_1_1` | ImageSize(1024,1024) → aspect_ratio="1:1" |
| `test_build_payload` | 包含 modalities, image_config |
| `test_parse_response_with_images` | 从 images[0].image_url.url 提取 base64 |
| `test_parse_response_no_images_raises` | 无 images 字段抛 ImageGenApiError |
| `test_generate_from_text_success` | mock httpx，完整流程返回 base64 data URL |
| `test_auth_header` | Authorization: Bearer {key} |

### Phase 4: factory.py + __init__.py — 组装

测试文件: `tests/backend/unit/test_image_gen_factory.py`

| 测试 | 验收标准 |
|------|---------|
| `test_default_creates_dashscope` | 默认 provider 返回 DashScopeProvider |
| `test_openrouter_creates_openrouter` | provider="openrouter" 返回 OpenRouterProvider |
| `test_invalid_provider_raises` | 无效值抛 ValueError |

### Phase 5: image_gen_client.py — 向后兼容层

测试文件: `tests/backend/unit/test_image_gen_client.py`（更新现有）

| 测试 | 验收标准 |
|------|---------|
| 现有所有 DashScope 测试 | 全部通过（回归） |
| `test_client_delegates_to_provider` | 验证内部委托给正确 provider |
| `test_size_string_parsing` | "1536*2688" 正确解析为 ImageSize |
| `test_exceptions_importable` | ImageGenApiError/TimeoutError 从原路径可导入 |

### Phase 6: 真实 API 集成测试

测试文件: `tests/backend/integration/test_real_api.py`（扩展现有）

| 测试 | 验收标准 |
|------|---------|
| `test_openrouter_generate_from_text` | 真实调用 OpenRouter，返回有效 base64 PNG |
| `test_openrouter_image_decodable` | base64 可解码为有效图片，尺寸 > 0 |
| `test_full_comic_flow_openrouter` | provider=openrouter 时完整漫画生成流程通过 |

跳过条件: `OPENROUTER_IMAGE_APIKEY` 未配置时 skip。

### Phase 7: 端到端验收

手动验收（启动完整应用）:

1. `.env` 设置 `IMAGE_GEN_PROVIDER=openrouter` + OpenRouter key
2. `python start.py` 启动前后端
3. 浏览器打开 → OK 手势触发 → 脚本生成 → 确认 → 漫画生成成功
4. 切换回 `IMAGE_GEN_PROVIDER=dashscope` → 重复流程 → 同样成功
5. 两种 provider 生成的漫画都能在 Gallery 中展示

## 8. 实现顺序总结

```
Phase 1: base.py (Protocol + ImageSize + retry + 异常)
    ↓ 验收: test_image_gen_base.py 全绿
Phase 2: dashscope_provider.py (提取现有逻辑)
    ↓ 验收: test_dashscope_provider.py 全绿
Phase 3: openrouter_provider.py (新增)
    ↓ 验收: test_openrouter_provider.py 全绿
Phase 4: factory.py + __init__.py (组装)
    ↓ 验收: test_image_gen_factory.py 全绿
Phase 5: image_gen_client.py (向后兼容改造) + config.py
    ↓ 验收: test_image_gen_client.py 全绿 + 现有全部测试回归通过
Phase 6: 真实 API 集成测试
    ↓ 验收: test_real_api.py OpenRouter 测试通过
Phase 7: 端到端手动验收
    ↓ 验收: 完整漫画生成流程两种 provider 都成功
```
