# MagicPose - AI 姿态创意海报生成器

> 基于 SOLID、KISS、DRY、YAGNI 原则的开发指南

## 目录

- [项目概览](#项目概览)
- [代码导航策略](#代码导航策略)
- [项目结构约定](#项目结构约定)
- [API 规范](#api-规范)
- [测试规范](#测试规范)
- [代码质量标准](#代码质量标准)
- [快速命令参考](#快速命令参考)
- [检查清单](#检查清单)

---

## 项目概览

**MagicPose** 是一个 AI 驱动的姿态创意海报生成器：用户对着摄像头摆造型 → MediaPipe 手势触发拍照 → GLM-4.6V 快速分析返回 5 个创意主题（仅名称+简述）→ 用户选择主题 → 内部 LLM 构思详细构图 prompt → Qwen Image 2.0 生成创意海报。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19, TypeScript 5.7, Vite 6, Tailwind CSS 4 |
| 后端 | FastAPI, Python 3.12 |
| 手势检测 | MediaPipe Hands |
| 视觉大模型 | GLM-4.6V（智谱 BigModel，OpenAI 兼容接口） |
| 图像生成 | Qwen Image 2.0（通义 DashScope 原生接口） |
| 包管理 | `uv`（Python）、`npm`（前端） |
| 配置管理 | `pydantic-settings` + `.env` 文件 |

### 核心工作流

```
摄像头 → 手势检测(MediaPipe) → 拍照 → 阶段1: GLM-4.6V 快速分析 → 返回5个主题(name+brief)
     → 用户选择主题 → 阶段2: GLM-4.6V 构思详细构图prompt → Qwen Image 2.0 生图 → 下载/分享
```

### 环境要求

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) 包管理器
- API 密钥：智谱 BigModel（GLM-4.6V）+ 通义 DashScope（Qwen Image 2.0）

---

## 代码导航策略

### 优先使用符号级导航

**核心原则：减少全文件读取，使用精确工具定位**

1. **了解模块结构** → `get_symbols_overview` / `find_symbol` 查看符号列表
2. **查找定义** → `find_symbol`（Serena）或 `Grep`（关键词搜索）
3. **查找引用** → `find_referencing_symbols` 或 `Grep`
4. **修改代码** → 定位符号 → `replace_symbol_body` / `insert_after_symbol` / `Edit`

### 读取策略

| 场景 | 推荐方法 |
|------|----------|
| 了解模块有哪些类/函数 | `get_symbols_overview` / `find_symbol(depth=1)` |
| 查找特定符号定义 | `find_symbol(include_body=True)` |
| 查找函数调用链 | `find_referencing_symbols` |
| 搜索文本/模式 | `Grep` / `search_for_pattern` |
| 修改已知位置代码 | `Edit` / `replace_symbol_body` |
| 新功能开发 | 先读接口文件(schemas/services) → 按需深入 |

### 禁止行为

- ❌ 频繁 `Read` 整个文件"了解结构"——使用 `get_symbols_overview` 替代
- ❌ 盲目搜索后逐个读取——先缩窄范围
- ❌ 不了解架构直接猜测位置

---

## 项目结构约定

```
MagicPose/
├── backend/                  # FastAPI 后端
│   ├── run.py                # 后端启动入口 (uvicorn)
│   └── app/
│       ├── main.py           # FastAPI 应用工厂 + lifespan + 中间件
│       ├── config.py         # Pydantic Settings（从 .env 加载）
│       ├── dependencies.py   # FastAPI 依赖注入
│       ├── logging_config.py # 日志配置（文件+控制台）
│       ├── middleware.py      # 请求 ID 中间件
│       ├── routers/          # API 路由层
│       │   ├── analyze.py    # POST /api/analyze — 姿态分析
│       │   ├── generate.py   # POST /api/generate — 海报生成
│       │   └── history.py    # GET  /api/history — 历史记录
│       ├── schemas/          # Pydantic 请求/响应模型
│       │   ├── common.py     # ApiResponse 统一信封 + ErrorCode
│       │   ├── analyze.py    # AnalyzeRequest / AnalyzeResponse / StyleOption
│       │   ├── generate.py   # GenerateRequest / GenerateResponse
│       │   └── history.py    # HistoryItem / HistoryResponse
│       ├── services/         # 业务逻辑层
│       │   ├── llm_client.py       # GLM-4.6V 视觉 LLM 客户端
│       │   ├── image_gen_client.py # Qwen Image 2.0 图像生成客户端
│       │   ├── analyze_service.py  # 阶段1: 快速分析，返回5个主题
│       │   ├── generate_service.py # 阶段2: compose prompt + Qwen 生图
│       │   └── history_service.py  # 历史记录管理
│       ├── storage/          # 持久化
│       │   └── file_storage.py     # 基于文件的海报/照片存储
│       └── prompts/          # Prompt 模板（两阶段）
│           ├── analyze_prompt.py   # 阶段1: 快速分析提示词
│           └── compose_prompt.py   # 阶段2: 详细构图提示词
├── frontend/                 # React 19 + TypeScript + Vite
│   ├── vite.config.ts        # Vite 配置 + API 代理
│   ├── tsconfig.app.json     # TypeScript 严格模式
│   └── src/
│       ├── main.tsx          # 应用入口
│       ├── App.tsx           # 根组件 + 状态机
│       ├── components/       # UI 组件（每个组件一个目录）
│       │   ├── CameraView/       # 摄像头视图
│       │   ├── Countdown/        # 倒计时动画
│       │   ├── GestureOverlay/   # 手势识别叠加层
│       │   ├── StyleSelection/   # 风格选择
│       │   ├── StyleCard/        # 风格卡片
│       │   ├── PosterDisplay/    # 海报展示 + 下载
│       │   ├── HistoryList/      # 历史记录列表
│       │   ├── ErrorDisplay.tsx  # 错误展示
│       │   └── LoadingSpinner.tsx# 加载动画
│       ├── hooks/            # React Hooks
│       │   ├── useCamera.ts          # 摄像头管理
│       │   ├── useCountdown.ts       # 倒计时逻辑
│       │   ├── useGestureDetector.ts # 手势检测
│       │   └── useMediaPipeHands.ts  # MediaPipe Hands 初始化
│       ├── services/         # API 客户端
│       │   └── api.ts             # fetch 封装 + 端点函数
│       ├── types/            # TypeScript 类型定义
│       │   └── index.ts          # AppState 枚举 + 接口
│       ├── constants/        # 常量配置
│       │   └── index.ts          # API_BASE_URL / ENDPOINTS / TIMEOUTS
│       └── utils/            # 工具函数
│           ├── captureFrame.ts    # Canvas 帧捕获
│           └── gestureAlgo.ts     # 手势识别算法
├── tests/                    # 统一测试目录
│   ├── backend/
│   │   ├── conftest.py       # 共享 fixtures（client, sample_image 等）
│   │   ├── unit/             # 单元测试（139 个用例）
│   │   └── integration/      # 集成测试（需真实 API Key）
│   ├── frontend/
│   │   ├── unit/             # Vitest 单元测试
│   │   └── e2e/              # Playwright E2E 测试
│   └── e2e/                  # 全栈端到端测试
├── docs/                     # 设计文档
├── .env.example              # 环境变量模板
├── pyproject.toml            # Python 项目配置（uv + pytest）
└── start.py                  # 一键启动脚本（前后端同时启动）
```

### 后端模块依赖关系

```
              ┌──────────┐
              │ routers/ │   HTTP 接口层，依赖注入 Settings
              └────┬─────┘
                   │
              ┌────▼─────┐
              │ services/│   业务编排（两阶段: analyze → compose → generate）
              └────┬─────┘
                   │
    ┌──────┬───────┼────────┬──────────┐
    │      │       │        │          │
┌───▼──┐ ┌▼──────┐ │   ┌───▼────┐ ┌───▼──────┐
│prompts│ │llm_   │ │   │image_  │ │ storage/ │
│analyze│ │client │ │   │gen_    │ │history_  │
│compose│ │       │ │   │client  │ │service   │
└──────┘ └───┬───┘ │   └────────┘ └──────────┘
              │     │
              └──┬──┘
                 │
            ┌────▼─────┐
            │ schemas/ │   Pydantic 模型，纯数据结构
            │ config   │   Settings 配置
            └──────────┘
```

**依赖方向**: `routers → services → (llm_client | image_gen_client | prompts | storage) → schemas/config`

**两阶段 LLM 调用流程**: `analyze_service` 使用 `ANALYZE_PROMPT`（快速分析，返回 5 个主题），`generate_service._compose_prompt` 使用 `COMPOSE_PROMPT`（详细构图），再调 `ImageGenClient` 生图。

---

## API 规范

### 统一响应信封

所有 API 返回 `ApiResponse` 信封格式：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

错误时 `code` 为非零值，`data` 为 `null`。

### 端点定义

| 端点 | 方法 | 请求体 | 响应 data |
|------|------|--------|-----------|
| `/api/analyze` | POST | `{ image_base64, image_format }` | `{ options: StyleOption[] }` （恰好 5 个，仅 name+brief） |
| `/api/generate` | POST | `{ image_base64, image_format, style_name, style_brief }` | `{ poster_url, thumbnail_url, history_id }` |
| `/api/history` | GET | Query: `page`, `page_size` | `{ items, total, page, page_size, total_pages }` |
| `/health` | GET | - | `{ status, app }` |

### 关键约定

- **字段命名**: 后端全部使用 `snake_case`（`image_base64`、`style_name`、`page_size`）
- **图片传输**: Base64 编码字符串，格式由 `image_format` 字段指定（`jpeg`/`png`/`webp`）
- **前端代理**: Vite 开发服务器代理 `/api` 和 `/data` 到 `http://localhost:8888`

### 错误码体系

```python
class ErrorCode:
    BAD_REQUEST = 40001          # 通用请求错误
    UNSUPPORTED_FORMAT = 40002   # 不支持的图片格式
    IMAGE_TOO_LARGE = 40003      # 图片过大
    VISION_LLM_FAILED = 50001    # 阶段1: 分析 LLM 调用失败
    VISION_LLM_INVALID = 50002   # 阶段1: 分析 LLM 响应解析失败
    IMAGE_GEN_FAILED = 50003     # Qwen 生图失败
    IMAGE_DOWNLOAD_FAILED = 50004 # 图片下载失败
    INTERNAL_ERROR = 50005       # 内部错误
    COMPOSE_LLM_FAILED = 50006   # 阶段2: 构图 LLM 调用失败
    COMPOSE_LLM_INVALID = 50007  # 阶段2: 构图 LLM 响应解析失败
```

---

## 测试规范

### 三层测试架构

```
tests/
├── backend/
│   ├── unit/            # 单元测试：隔离、快速、Mock 外部依赖
│   │   ├── test_analyze.py
│   │   ├── test_generate.py
│   │   ├── test_llm_client.py
│   │   ├── test_image_gen_client.py
│   │   ├── test_config.py
│   │   ├── test_app.py
│   │   ├── test_file_storage.py
│   │   ├── test_history_service.py
│   │   ├── test_history.py
│   │   ├── test_schemas_common.py
│   │   ├── test_system_prompt.py
│   │   ├── test_logging_config.py
│   │   ├── test_middleware.py
│   │   └── test_dependencies.py
│   └── integration/     # 集成测试：真实 API 调用
│       └── test_real_api.py
├── frontend/
│   ├── unit/            # Vitest 单元测试
│   └── e2e/             # Playwright E2E 测试
└── e2e/                 # 全栈端到端测试
    └── e2e_test.py
```

### 共享 Fixtures（tests/backend/conftest.py）

- `tmp_data_dir` — 创建临时 data 目录结构 + 设置环境变量
- `client` — FastAPI ASGI 测试客户端（httpx AsyncClient）
- `sample_image_base64` — 100x100 红色 JPEG 图片的 Base64
- `mock_llm_options` — 模拟分析 LLM 返回的 5 个主题选项（name+brief）
- `mock_llm_response_text` — 模拟分析 LLM JSON 响应
- `mock_compose_response` — 模拟构图 LLM 返回的详细 prompt JSON
- `mock_image_gen_b64` — 模拟生成的蓝色 64x64 PNG

### 测试命名约定

```python
# 格式: test_<被测方法>_<场景>_<预期结果>
def test_analyze_photo_valid_image_returns_options(): ...
def test_generate_artwork_llm_timeout_returns_error(): ...

# 参数化测试
@pytest.mark.parametrize("format_str", ["jpeg", "png", "webp"])
def test_analyze_accepts_supported_formats(format_str): ...
```

### pytest 配置

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests/backend"]
```

conftest.py 自动将 `backend/` 加入 `sys.path`，支持 `from app.*` 导入。

---

## 代码质量标准

### Python 后端

- **框架**: FastAPI + Pydantic v2
- **HTTP 客户端**: `httpx`（async），已配置重试 + 指数退避
- **配置**: `pydantic-settings`，从 `../.env`（项目根目录）加载
- **日志**: `logging` 模块，按模块获取 logger
- **类型注解**: 推荐完整类型注解（Python 3.12 风格）
- **异常体系**: 每个客户端定义专属异常（`LLMTimeoutError`、`ImageGenApiError` 等）

```python
# 良好的示例 — 后端服务函数（两阶段 LLM）
async def analyze_photo(
    image_base64: str, image_format: str, settings: Settings,
) -> list[StyleOption]:
    """阶段1: 分析照片，返回 5 个主题选项（仅名称+简述）。"""
    llm = LLMClient(settings)
    content = await llm.chat_with_vision(
        ANALYZE_PROMPT, image_base64, image_format,
        "请分析照片中的人物，生成 5 个创意主题选项",
        temperature=0.8,
    )
    data = LLMClient.extract_json_from_content(content)
    # ...校验恰好 5 个选项，构造 StyleOption 列表
```

### TypeScript 前端

- **框架**: React 19（函数组件 + Hooks）
- **构建**: Vite 6 + `@vitejs/plugin-react`
- **样式**: Tailwind CSS 4（`@tailwindcss/vite` 插件）
- **类型**: `tsconfig.app.json` 启用 `strict: true`
- **组件结构**: 每个组件一个目录，包含 `.tsx` + `.test.tsx`
- **状态管理**: App 级状态机（`AppState` 枚举），不使用全局状态库

```typescript
// 良好的示例 — React 组件
interface CameraViewProps {
  onPhotoCapture: (base64: string) => void;
}

export function CameraView({ onPhotoCapture }: CameraViewProps) {
  // ...
}
```

### SOLID / KISS / DRY / YAGNI 原则

- **S（单一职责）**: 路由层(routers)仅处理 HTTP，业务逻辑在 services，数据模型在 schemas
- **O（开闭原则）**: 通过 Pydantic 模型扩展请求/响应，不修改路由签名
- **D（依赖倒置）**: 路由依赖 Settings 抽象注入，服务函数接受 Settings 参数
- **KISS**: 避免过度抽象——当前业务简单，不需要 Repository/UnitOfWork 模式
- **DRY**: 共享 fixtures 在 conftest.py，共享类型在 `types/index.ts`，共享常量在 `constants/index.ts`
- **YAGNI**: 仅实现当前需要的功能，不预留未来扩展点

### 代码格式

```python
# 导入顺序：标准库 → 第三方 → 本地
import json
import logging

import httpx
from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.common import ApiResponse

# 函数长度：≤ 50 行（复杂逻辑抽取子函数）
# 类长度：≤ 300 行（考虑拆分）
```

---

## 快速命令参考

```bash
# 一键启动（前后端）
python start.py

# 单独启动后端
uv run python backend/run.py

# 单独启动前端
cd frontend && npm run dev

# 后端单元测试
uv run pytest tests/backend/unit/ -v

# 后端集成测试（需 API Key）
uv run pytest tests/backend/integration/test_real_api.py -v -s

# 前端单元测试
cd frontend && npx vitest run

# 前端 E2E 测试
cd frontend && npx playwright test

# 全栈 E2E 测试
uv run python tests/e2e/e2e_test.py

# 前端构建
cd frontend && npm run build

# 前端 lint
cd frontend && npm run lint
```

---

## 检查清单

### 提交前必检

- [ ] `uv run pytest tests/backend/unit/ -v` 全部通过
- [ ] `cd frontend && npx vitest run` 全部通过
- [ ] 新/修改的后端代码有对应测试
- [ ] API 字段使用 `snake_case`（`image_base64`、`style_name`）
- [ ] 前后端类型定义与 schemas 保持同步
- [ ] 遵循 SOLID / KISS / DRY / YAGNI
- [ ] 无重复代码
- [ ] 函数/类有文档字符串或 JSDoc

### Code Review 标准

- [ ] Pydantic 模型字段有 `description` 和合适的验证（`min_length`、`pattern` 等）
- [ ] 异常处理使用自定义异常类，不裸 `raise Exception`
- [ ] HTTP 客户端使用 `httpx`，不使用 `requests`
- [ ] React 组件使用函数式写法 + TypeScript 接口定义 Props
- [ ] 日志使用 `logging.getLogger(__name__)`，不使用 `print()`
- [ ] 依赖方向正确：`routers → services → clients/storage → schemas`
