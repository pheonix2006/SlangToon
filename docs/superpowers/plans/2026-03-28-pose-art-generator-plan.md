# Pose Art Generator 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个交互式艺术 Web 应用，用户通过摄像头 OK 手势拍照，Vision LLM 分析照片生成创意风格选项，用户选择后调用 Qwen Image 2.0 生成艺术海报。

**Architecture:** 前后端分离架构。前端 React + TypeScript + Vite 负责摄像头采集、MediaPipe 手势检测和 UI 交互；后端 Python FastAPI 负责 AI API 调用（Vision LLM 分析 + Qwen Image 2.0 生成），通过 REST API 通信。

**Tech Stack:**
- 前端: React 18 + TypeScript 5.5 + Vite 5.4 + Tailwind CSS 3.4 + @mediapipe/hands
- 后端: Python 3.11+ + FastAPI + Uvicorn + httpx + pydantic-settings + Pillow
- 测试: pytest + pytest-asyncio (后端)

---

## Task 1: 项目初始化

**目标:** 创建后端和前端的目录结构、依赖配置和 git 仓库。

**Files:**
- `E:/Project/1505creative_art/.gitignore`
- `E:/Project/1505creative_art/backend/requirements.txt`
- `E:/Project/1505creative_art/backend/.env.example`
- `E:/Project/1505creative_art/backend/data/.gitkeep`
- `E:/Project/1505creative_art/backend/tests/__init__.py`
- `E:/Project/1505creative_art/backend/app/__init__.py`

**Steps:**

- [ ] 在项目根目录初始化 git 仓库
  ```bash
  cd E:/Project/1505creative_art && git init
  ```
  预期输出: `Initialized empty Git repository in ...`

- [ ] 创建 `.gitignore` 文件
  ```
  # Python
  __pycache__/
  *.py[cod]
  *.egg-info/
  .venv/
  venv/
  .env

  # Node
  node_modules/
  dist/
  .vite/

  # IDE
  .idea/
  .vscode/
  *.swp

  # OS
  .DS_Store
  Thumbs.db

  # Data
  backend/data/photos/
  backend/data/posters/
  backend/data/history.json

  # Build
  *.log
  .pytest_cache/
  .coverage
  ```

- [ ] 创建后端目录结构和 `requirements.txt`
  ```
  # Web Framework
  fastapi>=0.110.0
  uvicorn[standard]>=0.29.0

  # HTTP Client
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
  ```

- [ ] 创建 `backend/.env.example`
  ```env
  # ===== 应用配置 =====
  APP_NAME=PoseArtGenerator
  APP_VERSION=1.0.0
  DEBUG=false
  HOST=0.0.0.0
  PORT=8000

  # ===== Vision LLM 配置 =====
  VISION_LLM_BASE_URL=https://api.openai.com/v1
  VISION_LLM_API_KEY=sk-your-vision-llm-api-key
  VISION_LLM_MODEL=gpt-4o
  VISION_LLM_MAX_TOKENS=4096
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

- [ ] 创建后端空 `__init__.py` 文件和 `data/.gitkeep`
  ```bash
  touch E:/Project/1505creative_art/backend/app/__init__.py
  touch E:/Project/1505creative_art/backend/tests/__init__.py
  mkdir -p E:/Project/1505creative_art/backend/data/photos
  mkdir -p E:/Project/1505creative_art/backend/data/posters
  touch E:/Project/1505creative_art/backend/data/.gitkeep
  ```

- [ ] 创建前端项目（Vite + React + TS）
  ```bash
  cd E:/Project/1505creative_art && npm create vite@latest frontend -- --template react-ts
  ```
  预期输出: 生成 `frontend/` 目录，包含 `package.json`, `vite.config.ts` 等

- [ ] 安装前端依赖
  ```bash
  cd E:/Project/1505creative_art/frontend && npm install
  npm install @mediapipe/hands tailwindcss postcss autoprefixer
  npm install -D @types/node
  npx tailwindcss init -p
  ```
  预期输出: 无报错，`node_modules/` 生成

- [ ] 配置 Tailwind CSS (`frontend/tailwind.config.ts`)
  ```typescript
  import type { Config } from 'tailwindcss'

  export default {
    content: [
      "./index.html",
      "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
      extend: {},
    },
    plugins: [],
  } satisfies Config
  ```

- [ ] 配置 `frontend/src/index.css` 添加 Tailwind 指令
  ```css
  @tailwind base;
  @tailwind components;
  @tailwind utilities;

  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background-color: #0a0a0a;
    color: #ffffff;
    overflow: hidden;
  }

  #root {
    width: 100vw;
    height: 100vh;
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build
  ```
  预期输出: `dist/` 目录生成，无 TypeScript 错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add -A && git commit -m "chore: 项目初始化 - 后端目录结构 + 前端 Vite+React+TS+Tailwind"
  ```

---

## Task 2: 后端配置模块

**目标:** 实现 pydantic-settings 配置加载、CORS 中间件、FastAPI 应用入口。

**Files:**
- `E:/Project/1505creative_art/backend/app/config.py`
- `E:/Project/1505creative_art/backend/app/dependencies.py`
- `E:/Project/1505creative_art/backend/app/main.py`
- `E:/Project/1505creative_art/backend/run.py`
- `E:/Project/1505creative_art/backend/.env`

**Steps:**

- [ ] 创建 `backend/app/config.py` — Settings 类
  ```python
  from pydantic_settings import BaseSettings, SettingsConfigDict


  class Settings(BaseSettings):
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
      vision_llm_max_tokens: int = 4096
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

- [ ] 创建 `backend/app/dependencies.py` — 依赖注入
  ```python
  from functools import lru_cache
  from app.config import Settings, get_settings


  @lru_cache
  def get_cached_settings() -> Settings:
      return get_settings()
  ```

- [ ] 创建 `backend/app/main.py` — FastAPI 应用入口
  ```python
  from contextlib import asynccontextmanager
  from fastapi import FastAPI
  from fastapi.middleware.cors import CORSMiddleware
  from fastapi.staticfiles import StaticFiles
  from pathlib import Path

  from app.config import get_settings


  @asynccontextmanager
  async def lifespan(app: FastAPI):
      settings = get_settings()
      # 启动时创建存储目录
      Path(settings.photo_storage_dir).mkdir(parents=True, exist_ok=True)
      Path(settings.poster_storage_dir).mkdir(parents=True, exist_ok=True)
      Path(settings.history_file).parent.mkdir(parents=True, exist_ok=True)
      yield


  def create_app() -> FastAPI:
      settings = get_settings()
      app = FastAPI(
          title=settings.app_name,
          version=settings.app_version,
          lifespan=lifespan,
      )

      # CORS 中间件
      app.add_middleware(
          CORSMiddleware,
          allow_origins=settings.cors_origin_list,
          allow_credentials=True,
          allow_methods=["*"],
          allow_headers=["*"],
      )

      # 静态文件服务
      data_dir = Path("data")
      if data_dir.exists():
          app.mount("/data", StaticFiles(directory="data"), name="data")

      return app


  app = create_app()


  @app.get("/health")
  async def health_check():
      return {"status": "ok", "app": "PoseArtGenerator"}
  ```

- [ ] 创建 `backend/run.py` — 启动脚本
  ```python
  import uvicorn
  from app.config import get_settings

  if __name__ == "__main__":
      settings = get_settings()
      uvicorn.run(
          "app.main:app",
          host=settings.host,
          port=settings.port,
          reload=settings.debug,
      )
  ```

- [ ] 创建 `backend/.env`（从 .env.example 复制，填入真实 key 或保留占位）
  ```bash
  cp E:/Project/1505creative_art/backend/.env.example E:/Project/1505creative_art/backend/.env
  ```

- [ ] 安装后端依赖并验证启动
  ```bash
  cd E:/Project/1505creative_art/backend && pip install -r requirements.txt
  python -c "from app.config import Settings; s = Settings(); print(f'App: {s.app_name}')"
  ```
  预期输出: `App: PoseArtGenerator`

- [ ] 验证 uvicorn 启动（快速检查）
  ```bash
  cd E:/Project/1505creative_art/backend && timeout 5 python run.py 2>&1 || true
  ```
  预期输出包含: `Uvicorn running on http://0.0.0.0:8000`

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/config.py backend/app/dependencies.py backend/app/main.py backend/run.py backend/.env.example && git commit -m "feat(backend): 配置模块 - pydantic-settings / CORS / FastAPI 入口"
  ```

---

## Task 3: 后端 Pydantic Schema 定义

**目标:** 定义所有 API 的请求/响应 Pydantic 模型和公共错误处理。

**Files:**
- `E:/Project/1505creative_art/backend/app/schemas/__init__.py`
- `E:/Project/1505creative_art/backend/app/schemas/analyze.py`
- `E:/Project/1505creative_art/backend/app/schemas/generate.py`
- `E:/Project/1505creative_art/backend/app/schemas/history.py`
- `E:/Project/1505creative_art/backend/app/schemas/common.py`

**Steps:**

- [ ] 创建 `backend/app/schemas/__init__.py`
  ```python
  ```

- [ ] 创建 `backend/app/schemas/common.py` — 公共响应信封和错误码
  ```python
  from typing import Any, Optional
  from pydantic import BaseModel


  class ApiResponse(BaseModel):
      """统一响应信封"""
      code: int = 0
      message: str = "success"
      data: Optional[Any] = None


  class ErrorResponse(BaseModel):
      """错误响应"""
      code: int
      message: str
      data: Optional[Any] = None


  # 错误码常量
  class ErrorCode:
      BAD_REQUEST = 40001
      UNSUPPORTED_FORMAT = 40002
      IMAGE_TOO_LARGE = 40003
      VISION_LLM_FAILED = 50001
      VISION_LLM_INVALID = 50002
      IMAGE_GEN_FAILED = 50003
      IMAGE_DOWNLOAD_FAILED = 50004
      INTERNAL_ERROR = 50005
  ```

- [ ] 创建 `backend/app/schemas/analyze.py`
  ```python
  from pydantic import BaseModel, Field


  class AnalyzeRequest(BaseModel):
      image_base64: str = Field(
          ...,
          description="Base64 编码的图片（不含 data:image/xxx;base64, 前缀）",
          min_length=1,
      )
      image_format: str = Field(
          default="jpeg",
          description="图片格式：jpeg / png / webp",
          pattern=r"^(jpeg|png|webp)$",
      )


  class StyleOption(BaseModel):
      name: str = Field(..., description="风格名称")
      brief: str = Field(..., description="给用户看的简略描述")
      prompt: str = Field(..., description="给生图模型的详细提示词")


  class AnalyzeResponse(BaseModel):
      options: list[StyleOption] = Field(
          ...,
          description="风格选项列表",
          min_length=1,
          max_length=3,
      )
  ```

- [ ] 创建 `backend/app/schemas/generate.py`
  ```python
  from pydantic import BaseModel, Field


  class GenerateRequest(BaseModel):
      image_base64: str = Field(
          ...,
          description="Base64 编码的原始照片",
          min_length=1,
      )
      image_format: str = Field(
          default="jpeg",
          description="图片格式：jpeg / png / webp",
          pattern=r"^(jpeg|png|webp)$",
      )
      prompt: str = Field(
          ...,
          description="选中的详细生图提示词",
          min_length=1,
          max_length=2000,
      )
      style_name: str = Field(
          ...,
          description="选中的风格名称",
          min_length=1,
      )


  class GenerateResponse(BaseModel):
      poster_url: str = Field(..., description="海报图片的访问 URL")
      thumbnail_url: str = Field(..., description="缩略图访问 URL")
      history_id: str = Field(..., description="历史记录 ID（UUID）")
  ```

- [ ] 创建 `backend/app/schemas/history.py`
  ```python
  from pydantic import BaseModel, Field
  from datetime import datetime


  class HistoryItem(BaseModel):
      id: str = Field(..., description="记录唯一 ID")
      style_name: str = Field(..., description="使用的风格名称")
      prompt: str = Field(..., description="使用的生图提示词")
      poster_url: str = Field(..., description="海报图片 URL")
      thumbnail_url: str = Field(..., description="缩略图 URL")
      photo_url: str = Field("", description="原始照片 URL")
      created_at: str = Field(..., description="创建时间，ISO 8601")


  class HistoryResponse(BaseModel):
      items: list[HistoryItem] = Field(..., description="当前页记录列表")
      total: int = Field(..., description="总记录数")
      page: int = Field(..., description="当前页码")
      page_size: int = Field(..., description="每页条数")
      total_pages: int = Field(..., description="总页数")
  ```

- [ ] 验证模块导入
  ```bash
  cd E:/Project/1505creative_art/backend && python -c "from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse; print('schemas OK')"
  ```
  预期输出: `schemas OK`

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/schemas/ && git commit -m "feat(backend): Pydantic Schema 定义 - analyze/generate/history 请求响应模型"
  ```

---

## Task 4: 后端 LLM 客户端 — Vision LLM 调用

**目标:** 实现 OpenAI-compatible Vision LLM 客户端，包含请求构建、JSON 提取、错误处理和重试。

**Files:**
- `E:/Project/1505creative_art/backend/app/services/__init__.py`
- `E:/Project/1505creative_art/backend/app/services/llm_client.py`
- `E:/Project/1505creative_art/backend/tests/test_llm_client.py`

**Steps:**

- [ ] 创建 `backend/app/services/__init__.py`
  ```python
  ```

- [ ] 编写测试文件 `backend/tests/test_llm_client.py`
  ```python
  import json
  import pytest
  from unittest.mock import AsyncMock, patch, MagicMock
  import httpx

  from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError, LLMResponseError


  @pytest.fixture
  def client():
      from app.config import Settings
      settings = Settings(
          vision_llm_base_url="https://api.example.com/v1",
          vision_llm_api_key="sk-test",
          vision_llm_model="test-model",
          vision_llm_max_tokens=100,
          vision_llm_timeout=10,
          vision_llm_max_retries=2,
      )
      return LLMClient(settings)


  class TestLLMClientExtractJson:

      def test_pure_json(self):
          content = '{"options": [{"name": "A", "brief": "B", "prompt": "C"}]}'
          result = LLMClient.extract_json_from_content(content)
          assert result["options"][0]["name"] == "A"

      def test_markdown_wrapped_json(self):
          content = '```json\n{"options": []}\n```'
          result = LLMClient.extract_json_from_content(content)
          assert result == {"options": []}

      def test_invalid_json_raises(self):
          with pytest.raises(json.JSONDecodeError):
              LLMClient.extract_json_from_content("not json")


  class TestLLMClientChat:

      @pytest.mark.asyncio
      async def test_successful_call(self, client):
          mock_response = MagicMock()
          mock_response.json.return_value = {
              "choices": [{"message": {"content": '{"options": [{"name": "T", "brief": "B", "prompt": "P"}]}'}}]
          }
          with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_response)))
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              result = await client.chat_with_vision("sys", "fake_b64", "jpeg", "analyze")
          assert "options" in json.loads(result)

      @pytest.mark.asyncio
      async def test_4xx_no_retry(self, client):
          mock_resp = MagicMock()
          mock_resp.status_code = 401
          mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_resp)
          with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_resp)))
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              with pytest.raises(LLMApiError):
                  await client.chat_with_vision("sys", "fake", "jpeg", "text")

      @pytest.mark.asyncio
      async def test_timeout_retries_then_raises(self, client):
          with patch("app.services.llm_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(
                  return_value=MagicMock(post=AsyncMock(side_effect=httpx.TimeoutException("timeout")))
              )
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              with pytest.raises(LLMTimeoutError, match="重试"):
                  await client.chat_with_vision("sys", "fake", "jpeg", "text")
  ```

- [ ] 运行测试确认失败（Red）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_llm_client.py -v 2>&1 | head -20
  ```
  预期输出: 测试失败（模块不存在）

- [ ] 创建 `backend/app/services/llm_client.py`
  ```python
  import httpx
  import json
  import re
  import asyncio
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

      async def chat_with_vision(
          self,
          system_prompt: str,
          image_base64: str,
          image_format: str,
          user_text: str,
          temperature: float = 0.8,
      ) -> str:
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
                          f"{self.base_url}/chat/completions",
                          headers=self._build_headers(),
                          json=payload,
                      )
                      response.raise_for_status()
                      data = response.json()
                      return data["choices"][0]["message"]["content"]
              except httpx.TimeoutException as e:
                  last_exception = e
                  if attempt < self.max_retries:
                      await asyncio.sleep(2 ** attempt)
                  continue
              except httpx.HTTPStatusError as e:
                  last_exception = e
                  if 400 <= e.response.status_code < 500:
                      raise LLMApiError(
                          f"LLM API 错误: {e.response.status_code}"
                      ) from e
                  if attempt < self.max_retries:
                      await asyncio.sleep(2 ** attempt)
                  continue
              except (KeyError, IndexError) as e:
                  raise LLMResponseError(f"LLM 响应结构异常: {e}") from e

          raise LLMTimeoutError(
              f"LLM 超时，已重试 {self.max_retries} 次: {last_exception}"
          )

      @staticmethod
      def extract_json_from_content(content: str) -> dict:
          content = content.strip()
          pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
          match = re.search(pattern, content, re.DOTALL)
          if match:
              content = match.group(1).strip()
          return json.loads(content)


  class LLMTimeoutError(Exception):
      pass


  class LLMApiError(Exception):
      pass


  class LLMResponseError(Exception):
      pass
  ```

- [ ] 运行测试确认通过（Green）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_llm_client.py -v
  ```
  预期输出: 所有测试 PASS

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/services/llm_client.py backend/tests/test_llm_client.py && git commit -m "feat(backend): Vision LLM 客户端 - OpenAI-compatible 调用 + JSON 提取 + 重试"
  ```

---

## Task 5: 后端 LLM 客户端 — Qwen Image 2.0 调用

**目标:** 实现 Qwen Image 2.0 图生图客户端，包含指数退避重试、URL/Base64 双格式响应解析。

**Files:**
- `E:/Project/1505creative_art/backend/app/services/image_gen_client.py`
- `E:/Project/1505creative_art/backend/tests/test_image_gen_client.py`

**Steps:**

- [ ] 编写测试 `backend/tests/test_image_gen_client.py`
  ```python
  import base64
  import pytest
  from unittest.mock import AsyncMock, patch, MagicMock
  from io import BytesIO
  from PIL import Image
  import httpx

  from app.services.image_gen_client import (
      ImageGenClient, ImageGenTimeoutError, ImageGenApiError,
      parse_qwen_image_response,
  )


  @pytest.fixture
  def client():
      from app.config import Settings
      settings = Settings(
          qwen_image_base_url="https://dashscope.example.com/compatible-mode/v1",
          qwen_image_api_key="sk-test",
          qwen_image_model="qwen-image-2.0",
          qwen_image_timeout=10,
          qwen_image_max_retries=2,
      )
      return ImageGenClient(settings)


  @pytest.fixture
  def fake_b64_png():
      img = Image.new("RGB", (64, 64), "blue")
      buf = BytesIO()
      img.save(buf, "PNG")
      return base64.b64encode(buf.getvalue()).decode()


  class TestParseQwenResponse:

      def test_openai_url(self):
          resp = {"data": [{"url": "https://example.com/img.png"}]}
          assert parse_qwen_image_response(resp) == "https://example.com/img.png"

      def test_openai_b64_json(self):
          resp = {"data": [{"b64_json": "abc123"}]}
          assert parse_qwen_image_response(resp) == "data:image/png;base64,abc123"

      def test_dashscope_native(self):
          resp = {"output": {"results": [{"url": "https://example.com/img.png"}]}}
          assert parse_qwen_image_response(resp) == "https://example.com/img.png"

      def test_empty_data_raises(self):
          with pytest.raises(ValueError, match="为空"):
              parse_qwen_image_response({"data": []})

      def test_unknown_format_raises(self):
          with pytest.raises(ValueError, match="未知"):
              parse_qwen_image_response({"foo": "bar"})


  class TestImageGenClient:

      @pytest.mark.asyncio
      async def test_generate_b64_response(self, client, fake_b64_png):
          mock_resp = MagicMock()
          mock_resp.json.return_value = {"data": [{"b64_json": fake_b64_png}]}
          with patch("app.services.image_gen_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=AsyncMock(return_value=mock_resp)))
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              result = await client.generate("prompt", "fake_img", "jpeg")
          assert isinstance(result, str) and len(result) > 0

      @pytest.mark.asyncio
      async def test_timeout_no_retry(self, client):
          with patch("app.services.image_gen_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(
                  return_value=MagicMock(post=AsyncMock(side_effect=httpx.TimeoutException("t")))
              )
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              with pytest.raises(ImageGenTimeoutError):
                  await client.generate("p", "i", "jpeg")

      @pytest.mark.asyncio
      async def test_5xx_retries(self, client):
          mock_500 = MagicMock()
          mock_500.status_code = 500
          mock_500.raise_for_status.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_500)
          mock_ok = MagicMock()
          mock_ok.json.return_value = {"data": [{"b64_json": "abc"}]}
          call_count = 0
          async def mock_post(*a, **kw):
              nonlocal call_count
              call_count += 1
              if call_count <= 2:
                  raise httpx.HTTPStatusError("500", request=MagicMock(), response=mock_500)
              return mock_ok
          with patch("app.services.image_gen_client.httpx.AsyncClient") as mock_cls:
              mock_cls.return_value.__aenter__ = AsyncMock(return_value=MagicMock(post=mock_post))
              mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
              with patch("app.services.image_gen_client.asyncio.sleep", new_callable=AsyncMock):
                  result = await client.generate("p", "i", "jpeg")
          assert call_count == 3
  ```

- [ ] 运行测试确认失败（Red）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_image_gen_client.py -v 2>&1 | head -10
  ```

- [ ] 创建 `backend/app/services/image_gen_client.py`
  ```python
  import httpx
  import base64
  import asyncio
  from app.config import Settings


  def parse_qwen_image_response(api_response: dict) -> str:
      """解析 Qwen Image 2.0 API 响应，提取图片 URL 或 Base64。"""
      if "data" in api_response:
          data_list = api_response["data"]
          if not data_list:
              raise ValueError("API 响应 data 数组为空")
          first_item = data_list[0]
          if "url" in first_item:
              return first_item["url"]
          elif "b64_json" in first_item:
              return f"data:image/png;base64,{first_item['b64_json']}"
          else:
              raise ValueError("data[0] 中没有 url 或 b64_json 字段")
      elif "output" in api_response:
          results = api_response["output"].get("results", [])
          if not results:
              raise ValueError("API 响应 output.results 为空")
          return results[0].get("url", "")
      else:
          raise ValueError(f"未知的 API 响应格式: {list(api_response.keys())}")


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
          size: str = "1024*1024",
      ) -> str:
          """图生图模式生成海报，返回 Base64 编码的图片。"""
          payload = {
              "model": self.model,
              "input": {
                  "prompt": prompt,
                  "ref_image": f"data:image/{image_format};base64,{image_base64}",
              },
              "parameters": {
                  "n": 1,
                  "size": size,
                  "ref_strength": 0.7,
                  "seed": -1,
              },
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
                      result = parse_qwen_image_response(data)
                      # 如果返回 URL，下载并转为 Base64
                      if result.startswith("http"):
                          img_resp = await client.get(result)
                          img_resp.raise_for_status()
                          return base64.b64encode(img_resp.content).decode("utf-8")
                      return result
              except httpx.TimeoutException as e:
                  raise ImageGenTimeoutError(
                      f"Image Gen 超时（不重试）: {e}"
                  ) from e
              except httpx.HTTPStatusError as e:
                  last_exception = e
                  if 400 <= e.response.status_code < 500:
                      raise ImageGenApiError(
                          f"Image Gen API 错误: {e.response.status_code}"
                      ) from e
                  if attempt < self.max_retries:
                      await asyncio.sleep(2 ** attempt)
                  continue
              except httpx.ConnectError as e:
                  last_exception = e
                  if attempt < self.max_retries:
                      await asyncio.sleep(2 ** attempt)
                  continue

          raise ImageGenTimeoutError(
              f"Image Gen 失败，已重试 {self.max_retries} 次: {last_exception}"
          )


  class ImageGenTimeoutError(Exception):
      pass


  class ImageGenApiError(Exception):
      pass
  ```

- [ ] 运行测试确认通过（Green）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_image_gen_client.py -v
  ```
  预期输出: 所有测试 PASS

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/services/image_gen_client.py backend/tests/test_image_gen_client.py && git commit -m "feat(backend): Qwen Image 2.0 客户端 - 图生图调用 + 指数退避重试 + 双格式解析"
  ```

---

## Task 6: 后端系统提示词 + 文件存储

**目标:** 实现 Vision LLM 系统提示词模板（来自 prompt-pipeline-spec A.5）和本地文件存储。

**Files:**
- `E:/Project/1505creative_art/backend/app/prompts/__init__.py`
- `E:/Project/1505creative_art/backend/app/prompts/system_prompt.py`
- `E:/Project/1505creative_art/backend/app/storage/__init__.py`
- `E:/Project/1505creative_art/backend/app/storage/file_storage.py`

**Steps:**

- [ ] 创建 `backend/app/prompts/__init__.py`
  ```python
  ```

- [ ] 创建 `backend/app/prompts/system_prompt.py` — 完整系统提示词（来自 prompt-pipeline-spec A.5）
  ```python
  SYSTEM_PROMPT = """你是一位世界级的视觉艺术总监与 AI 绘画提示词工程师。你擅长分析人物照片中的姿态、表情、服饰和场景元素，并将这些真实元素转化为令人惊艳的艺术创作概念。

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

如果输出 JSON 后还有任何额外内容，整个回复将被视为无效。"""
  ```

- [ ] 创建 `backend/app/storage/__init__.py`
  ```python
  ```

- [ ] 创建 `backend/app/storage/file_storage.py`
  ```python
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
          file_uuid = uuid.uuid4().hex
          date_str = self._today_str()
          ext = "jpg" if image_format == "jpeg" else image_format

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

      def save_poster(self, image_base64: str, uuid: str, date_str: str) -> dict:
          date_dir = self._ensure_date_dir(self.poster_dir, date_str)

          # 剥离可能的 data:image/png;base64, 前缀
          if image_base64.startswith("data:image"):
              image_base64 = image_base64.split(",", 1)[1]

          poster_name = f"{uuid}.png"
          poster_path = date_dir / poster_name
          image_data = base64.b64decode(image_base64)
          poster_path.write_bytes(image_data)

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

- [ ] 验证导入
  ```bash
  cd E:/Project/1505creative_art/backend && python -c "from app.prompts.system_prompt import SYSTEM_PROMPT; print(f'Prompt length: {len(SYSTEM_PROMPT)} chars')"
  ```
  预期输出: `Prompt length: 2700 chars`（约）

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/prompts/ backend/app/storage/ && git commit -m "feat(backend): 系统提示词模板 + 本地文件存储（照片/海报/缩略图）"
  ```

---

## Task 7: 后端 API — /api/analyze

**目标:** 实现照片分析接口，调用 Vision LLM 返回风格选项，包含完整错误处理。

**Files:**
- `E:/Project/1505creative_art/backend/app/routers/__init__.py`
- `E:/Project/1505creative_art/backend/app/routers/analyze.py`
- `E:/Project/1505creative_art/backend/app/services/analyze_service.py`
- `E:/Project/1505creative_art/backend/tests/conftest.py`
- `E:/Project/1505creative_art/backend/tests/test_analyze.py`

**Steps:**

- [ ] 创建 `backend/app/routers/__init__.py`
  ```python
  ```

- [ ] 创建 `backend/tests/conftest.py` — 测试 fixtures
  ```python
  import json
  import pytest
  import base64
  from io import BytesIO
  from PIL import Image
  from pathlib import Path
  from unittest.mock import AsyncMock, patch, MagicMock


  @pytest.fixture
  def sample_image_base64() -> str:
      img = Image.new("RGB", (100, 100), color="red")
      buf = BytesIO()
      img.save(buf, format="JPEG")
      return base64.b64encode(buf.getvalue()).decode("utf-8")


  @pytest.fixture
  def mock_llm_options():
      return [
          {"name": "风格A", "brief": "描述A", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt A"},
          {"name": "风格B", "brief": "描述B", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt B"},
          {"name": "风格C", "brief": "描述C", "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, prompt C"},
      ]


  @pytest.fixture
  def mock_llm_response_text(mock_llm_options):
      return json.dumps({"options": mock_llm_options})


  @pytest.fixture
  def mock_image_gen_b64():
      img = Image.new("RGB", (64, 64), "blue")
      buf = BytesIO()
      img.save(buf, format="PNG")
      return base64.b64encode(buf.getvalue()).decode("utf-8")
  ```

- [ ] 编写测试 `backend/tests/test_analyze.py`
  ```python
  import pytest
  from unittest.mock import AsyncMock, patch, MagicMock
  from fastapi.testclient import TestClient
  import json

  from app.main import app


  @pytest.fixture
  def client():
      return TestClient(app)


  class TestAnalyzeEndpoint:

      def test_analyze_success(self, client, sample_image_base64, mock_llm_response_text):
          mock_resp = MagicMock()
          mock_resp.json.return_value = {
              "choices": [{"message": {"content": mock_llm_response_text}}]
          }
          with patch("app.services.analyze_service.LLMClient") as MockLLM:
              mock_instance = MockLLM.return_value
              mock_instance.chat_with_vision = AsyncMock(return_value=mock_llm_response_text)
              resp = client.post("/api/analyze", json={
                  "image_base64": sample_image_base64,
                  "image_format": "jpeg",
              })
          assert resp.status_code == 200
          data = resp.json()
          assert data["code"] == 0
          assert len(data["data"]["options"]) == 3
          assert data["data"]["options"][0]["name"] == "风格A"

      def test_analyze_empty_image(self, client):
          resp = client.post("/api/analyze", json={"image_base64": "", "image_format": "jpeg"})
          assert resp.status_code in (400, 422)

      def test_analyze_invalid_format(self, client, sample_image_base64):
          resp = client.post("/api/analyze", json={"image_base64": sample_image_base64, "image_format": "bmp"})
          assert resp.status_code in (400, 422)

      def test_analyze_llm_timeout(self, client, sample_image_base64):
          with patch("app.services.analyze_service.LLMClient") as MockLLM:
              from app.services.llm_client import LLMTimeoutError
              mock_instance = MockLLM.return_value
              mock_instance.chat_with_vision = AsyncMock(side_effect=LLMTimeoutError("timeout"))
              resp = client.post("/api/analyze", json={
                  "image_base64": sample_image_base64,
                  "image_format": "jpeg",
              })
          assert resp.status_code == 200
          assert resp.json()["code"] == 50001

      def test_analyze_invalid_json_response(self, client, sample_image_base64):
          with patch("app.services.analyze_service.LLMClient") as MockLLM:
              mock_instance = MockLLM.return_value
              mock_instance.chat_with_vision = AsyncMock(return_value="not json at all")
              resp = client.post("/api/analyze", json={
                  "image_base64": sample_image_base64,
                  "image_format": "jpeg",
              })
          assert resp.status_code == 200
          assert resp.json()["code"] == 50002

      def test_analyze_markdown_wrapped_json(self, client, sample_image_base64, mock_llm_response_text):
          wrapped = f"```json\n{mock_llm_response_text}\n```"
          mock_resp = MagicMock()
          mock_resp.json.return_value = {
              "choices": [{"message": {"content": wrapped}}]
          }
          with patch("app.services.analyze_service.LLMClient") as MockLLM:
              mock_instance = MockLLM.return_value
              mock_instance.chat_with_vision = AsyncMock(return_value=wrapped)
              resp = client.post("/api/analyze", json={
                  "image_base64": sample_image_base64,
                  "image_format": "jpeg",
              })
          assert resp.status_code == 200
          assert len(resp.json()["data"]["options"]) == 3
  ```

- [ ] 运行测试确认失败（Red）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_analyze.py -v 2>&1 | head -10
  ```

- [ ] 创建 `backend/app/services/analyze_service.py`
  ```python
  from app.config import Settings
  from app.services.llm_client import LLMClient, LLMTimeoutError, LLMResponseError, LLMApiError
  from app.prompts.system_prompt import SYSTEM_PROMPT
  from app.schemas.analyze import StyleOption


  class AnalyzeError(Exception):
      def __init__(self, code: int, message: str):
          self.code = code
          self.message = message
          super().__init__(message)


  async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
      """分析照片，返回风格选项列表。直接 await async LLM 调用，无需线程包装。"""
      llm = LLMClient(settings)

      try:
          content = await llm.chat_with_vision(
              SYSTEM_PROMPT, image_base64, image_format,
              "请分析照片中的人物，生成 3 个创意风格选项",
              temperature=0.8,
          )
      except (LLMTimeoutError, LLMApiError) as e:
          raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

      # 解析 JSON
      try:
          data = LLMClient.extract_json_from_content(content)
      except Exception as e:
          raise AnalyzeError(50002, f"Vision LLM 返回格式异常: {e}") from e

      # 校验结构
      if not isinstance(data, dict) or "options" not in data:
          raise AnalyzeError(50002, "JSON 缺少 options 字段")

      options = data["options"]
      if not isinstance(options, list) or len(options) == 0:
          raise AnalyzeError(50002, f"options 应为非空数组，实际: {type(options)}")

      # 转为 StyleOption 对象
      style_options = []
      for i, opt in enumerate(options[:3]):
          if not isinstance(opt, dict):
              raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
          for field in ("name", "brief", "prompt"):
              if field not in opt or not opt[field]:
                  raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
          style_options.append(StyleOption(**opt))

      return style_options
  ```

- [ ] 创建 `backend/app/routers/analyze.py`
  ```python
  from fastapi import APIRouter, Depends
  from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
  from app.schemas.common import ApiResponse, ErrorCode
  from app.config import get_settings, Settings
  from app.services.analyze_service import analyze_photo, AnalyzeError

  router = APIRouter(prefix="/api", tags=["analyze"])


  @router.post("/analyze", response_model=ApiResponse)
  async def analyze_endpoint(request: AnalyzeRequest, settings: Settings = Depends(get_settings)):
      try:
          options = await analyze_photo(request.image_base64, request.image_format, settings)
          return ApiResponse(code=0, message="success", data=AnalyzeResponse(options=options).model_dump())
      except AnalyzeError as e:
          return ApiResponse(code=e.code, message=e.message, data=None)
      except Exception as e:
          return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
  ```

- [ ] 注册路由到 `backend/app/main.py`（在 create_app 函数中添加）
  ```python
  # 在 create_app() 中 app 创建后添加:
  from app.routers import analyze
  app.include_router(analyze.router)
  ```

- [ ] 运行测试确认通过（Green）
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/test_analyze.py -v
  ```
  预期输出: 所有测试 PASS

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/routers/analyze.py backend/app/services/analyze_service.py backend/tests/test_analyze.py backend/tests/conftest.py backend/app/main.py && git commit -m "feat(backend): /api/analyze 接口 - Vision LLM 分析照片 + 返回风格选项"
  ```

---

## Task 8: 后端 API — /api/generate

**目标:** 实现海报生成接口，调用 Qwen Image 2.0 图生图，保存海报和缩略图，写入历史记录。

**Files:**
- `E:/Project/1505creative_art/backend/app/routers/generate.py`
- `E:/Project/1505creative_art/backend/app/services/generate_service.py`
- `E:/Project/1505creative_art/backend/app/services/history_service.py`
- `E:/Project/1505creative_art/backend/tests/test_generate.py`

**Steps:**

- [ ] 创建 `backend/app/services/history_service.py`
  ```python
  import json
  import uuid
  from datetime import datetime, timezone
  from pathlib import Path


  class HistoryService:
      def __init__(self, history_file: str, max_records: int = 1000):
          self.history_file = Path(history_file)
          self.max_records = max_records

      def _load(self) -> list[dict]:
          if not self.history_file.exists():
              return []
          return json.loads(self.history_file.read_text(encoding="utf-8"))

      def _save(self, records: list[dict]):
          self.history_file.write_text(
              json.dumps(records, ensure_ascii=False, indent=2),
              encoding="utf-8",
          )

      def add(self, item: dict) -> str:
          records = self._load()
          item["id"] = item.get("id", str(uuid.uuid4()))
          item["created_at"] = item.get("created_at", datetime.now(timezone.utc).isoformat())
          records.insert(0, item)
          if len(records) > self.max_records:
              records = records[:self.max_records]
          self._save(records)
          return item["id"]

      def get_page(self, page: int = 1, page_size: int = 20) -> dict:
          records = self._load()
          total = len(records)
          total_pages = max(1, (total + page_size - 1) // page_size)
          start = (page - 1) * page_size
          items = records[start:start + page_size]
          return {
              "items": items,
              "total": total,
              "page": page,
              "page_size": page_size,
              "total_pages": total_pages,
          }
  ```

- [ ] 创建 `backend/app/services/generate_service.py`
  ```python
  from app.config import Settings
  from app.services.image_gen_client import ImageGenClient, ImageGenTimeoutError, ImageGenApiError
  from app.storage.file_storage import FileStorage
  from app.services.history_service import HistoryService


  class GenerateError(Exception):
      def __init__(self, code: int, message: str):
          self.code = code
          self.message = message
          super().__init__(message)


  async def generate_artwork(
      image_base64: str,
      image_format: str,
      prompt: str,
      style_name: str,
      settings: Settings,
      storage: FileStorage,
      history: HistoryService,
  ) -> dict:
      """生成海报，保存文件，写入历史记录。返回 GenerateResponse 数据。直接 await async 调用，无需线程包装。"""

      # 保存原始照片
      photo_info = storage.save_photo(image_base64, image_format)

      # 调用 Qwen Image（直接 await async generate 方法）
      gen_client = ImageGenClient(settings)
      try:
          poster_b64 = await gen_client.generate(prompt, image_base64, image_format)
      except ImageGenTimeoutError as e:
          raise GenerateError(50003, f"图片生成超时: {e}") from e
      except ImageGenApiError as e:
          raise GenerateError(50003, f"图片生成 API 错误: {e}") from e
      except Exception as e:
          raise GenerateError(50004, f"生成结果处理失败: {e}") from e

      # 保存海报和缩略图
      poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])

      # 写入历史记录
      history_id = history.add({
          "style_name": style_name,
          "prompt": prompt,
          "poster_url": poster_info["poster_url"],
          "thumbnail_url": poster_info["thumbnail_url"],
          "photo_url": photo_info["url"],
      })

      return {
          "poster_url": poster_info["poster_url"],
          "thumbnail_url": poster_info["thumbnail_url"],
          "history_id": history_id,
      }
  ```

- [ ] 创建 `backend/app/routers/generate.py`
  ```python
  from fastapi import APIRouter, Depends
  from app.schemas.generate import GenerateRequest, GenerateResponse
  from app.schemas.common import ApiResponse, ErrorCode
  from app.config import get_settings, Settings
  from app.storage.file_storage import FileStorage
  from app.services.history_service import HistoryService
  from app.services.generate_service import generate_artwork, GenerateError

  router = APIRouter(prefix="/api", tags=["generate"])


  @router.post("/generate", response_model=ApiResponse)
  async def generate_endpoint(request: GenerateRequest, settings: Settings = Depends(get_settings)):
      storage = FileStorage(settings.photo_storage_dir, settings.poster_storage_dir)
      history = HistoryService(settings.history_file, settings.max_history_records)

      try:
          result = await generate_artwork(
              request.image_base64,
              request.image_format,
              request.prompt,
              request.style_name,
              settings,
              storage,
              history,
          )
          return ApiResponse(code=0, message="success", data=result)
      except GenerateError as e:
          return ApiResponse(code=e.code, message=e.message, data=None)
      except Exception as e:
          return ApiResponse(code=ErrorCode.INTERNAL_ERROR, message=str(e), data=None)
  ```

- [ ] 编写测试 `backend/tests/test_generate.py`
  ```python
  import pytest
  from unittest.mock import AsyncMock, patch, MagicMock
  from fastapi.testclient import TestClient

  from app.main import app


  @pytest.fixture
  def client():
      return TestClient(app)


  class TestGenerateEndpoint:

      def test_generate_success(self, client, sample_image_base64, mock_image_gen_b64):
          with patch("app.services.generate_service.ImageGenClient") as MockGen:
              mock_instance = MockGen.return_value
              mock_instance.generate = AsyncMock(return_value=mock_image_gen_b64)
              resp = client.post("/api/generate", json={
                      "image_base64": sample_image_base64,
                      "image_format": "jpeg",
                      "prompt": "masterpiece, best quality, ultra-detailed, 8K resolution, test prompt",
                      "style_name": "测试风格",
                  })
          assert resp.status_code == 200
          data = resp.json()
          assert data["code"] == 0
          assert data["data"]["poster_url"].startswith("/data/posters/")
          assert data["data"]["thumbnail_url"].endswith("_thumb.png")
          assert len(data["data"]["history_id"]) > 0

      def test_generate_empty_prompt(self, client, sample_image_base64):
          resp = client.post("/api/generate", json={
              "image_base64": sample_image_base64,
              "image_format": "jpeg",
              "prompt": "",
              "style_name": "test",
          })
          assert resp.status_code in (400, 422)

      def test_generate_prompt_too_long(self, client, sample_image_base64):
          long_prompt = "x" * 2001
          resp = client.post("/api/generate", json={
              "image_base64": sample_image_base64,
              "image_format": "jpeg",
              "prompt": long_prompt,
              "style_name": "test",
          })
          assert resp.status_code in (400, 422)
  ```

- [ ] 创建 `backend/app/routers/history.py`（先创建空壳，下一 Task 补全）
  ```python
  from fastapi import APIRouter, Depends, Query
  from app.schemas.common import ApiResponse
  from app.config import get_settings, Settings
  from app.services.history_service import HistoryService

  router = APIRouter(prefix="/api", tags=["history"])


  @router.get("/history", response_model=ApiResponse)
  async def history_endpoint(
      page: int = Query(1, ge=1),
      page_size: int = Query(20, ge=1, le=100),
      settings: Settings = Depends(get_settings),
  ):
      history = HistoryService(settings.history_file, settings.max_history_records)
      result = history.get_page(page=page, page_size=page_size)
      return ApiResponse(code=0, message="success", data=result)
  ```

- [ ] 在 `backend/app/main.py` 追加注册 generate 和 history 路由
  ```python
  # 在已有的 app.include_router(analyze.router) 之后添加:
  from app.routers import generate, history
  app.include_router(generate.router)
  app.include_router(history.router)
  ```

- [ ] 运行所有后端测试
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/ -v
  ```
  预期输出: 所有测试 PASS

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/app/routers/generate.py backend/app/routers/history.py backend/app/services/generate_service.py backend/app/services/history_service.py backend/tests/test_generate.py backend/app/main.py && git commit -m "feat(backend): /api/generate 接口 + /api/history 接口 + 历史记录服务"
  ```

---

## Task 9: 后端测试补全 + 历史记录测试

**目标:** 补全 history 接口测试和端到端 API 验证。

**Files:**
- `E:/Project/1505creative_art/backend/tests/test_history.py`

**Steps:**

- [ ] 编写测试 `backend/tests/test_history.py`
  ```python
  import pytest
  from fastapi.testclient import TestClient

  from app.main import app


  @pytest.fixture
  def client():
      return TestClient(app)


  class TestHistoryEndpoint:

      def test_history_empty(self, client):
          resp = client.get("/api/history")
          assert resp.status_code == 200
          data = resp.json()
          assert data["code"] == 0
          assert data["data"]["items"] == []
          assert data["data"]["total"] == 0

      def test_history_default_pagination(self, client):
          resp = client.get("/api/history")
          data = resp.json()["data"]
          assert data["page"] == 1
          assert data["page_size"] == 20

      def test_history_custom_pagination(self, client):
          resp = client.get("/api/history?page=1&page_size=5")
          data = resp.json()["data"]
          assert data["page"] == 1
          assert data["page_size"] == 5

      def test_history_page_beyond_total(self, client):
          resp = client.get("/api/history?page=9999")
          data = resp.json()["data"]
          assert data["items"] == []

      def test_history_invalid_page(self, client):
          resp = client.get("/api/history?page=0")
          assert resp.status_code == 422

      def test_history_page_size_exceeds_limit(self, client):
          resp = client.get("/api/history?page_size=200")
          assert resp.status_code == 422
  ```

- [ ] 运行所有后端测试
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/ -v --tb=short
  ```
  预期输出: 所有测试 PASS（analyze + generate + history）

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add backend/tests/test_history.py && git commit -m "test(backend): 补全 history 接口测试 - 分页/边界/异常场景"
  ```

---

## Task 10: 前端 — 类型定义 + 常量 + 基础骨架

**目标:** 创建前端 TypeScript 类型、API 常量、App 状态机骨架和基础 CSS。

**Files:**
- `E:/Project/1505creative_art/frontend/src/types/index.ts`
- `E:/Project/1505creative_art/frontend/src/constants/index.ts`
- `E:/Project/1505creative_art/frontend/src/App.tsx`
- `E:/Project/1505creative_art/frontend/src/index.css`
- `E:/Project/1505creative_art/frontend/src/vite-env.d.ts`

**Steps:**

- [ ] 创建 `frontend/src/types/index.ts`
  ```typescript
  export enum AppState {
    CAMERA_READY = 'CAMERA_READY',
    COUNTDOWN = 'COUNTDOWN',
    PHOTO_TAKEN = 'PHOTO_TAKEN',
    ANALYZING = 'ANALYZING',
    STYLE_SELECTION = 'STYLE_SELECTION',
    GENERATING = 'GENERATING',
    POSTER_READY = 'POSTER_READY',
    HISTORY = 'HISTORY',
  }

  export type GestureType = 'ok' | 'open_palm' | 'none';

  export interface GestureEvent {
    gesture: GestureType;
    confidence: number;
    detectedAt: number;
  }

  export interface StyleOption {
    name: string;
    brief: string;
    prompt: string;
  }

  export interface AnalyzeResponse {
    code: number;
    message: string;
    data: {
      options: StyleOption[];
    };
  }

  export interface GenerateResponse {
    code: number;
    message: string;
    data: {
      poster_url: string;
      thumbnail_url: string;
      history_id: string;
    };
  }

  export interface HistoryItem {
    id: string;
    photo_url: string;
    poster_url: string;
    thumbnail_url: string;
    style_name: string;
    prompt: string;
    created_at: string;
  }

  export interface HistoryResponse {
    code: number;
    message: string;
    data: {
      items: HistoryItem[];
      total: number;
      page: number;
      page_size: number;
      total_pages: number;
    };
  }

  export interface ApiError {
    code: string;
    message: string;
    retryable: boolean;
  }
  ```

- [ ] 创建 `frontend/src/constants/index.ts`
  ```typescript
  export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

  export const API_ENDPOINTS = {
    ANALYZE: '/api/analyze',
    GENERATE: '/api/generate',
    HISTORY: '/api/history',
  } as const;

  export const TIMEOUTS = {
    ANALYZE_REQUEST: 60_000,
    GENERATE_REQUEST: 120_000,
    HISTORY_REQUEST: 10_000,
  } as const;

  export const RETRY_CONFIG = {
    ANALYZE: { maxRetries: 2, delayMs: 2000 },
    GENERATE: { maxRetries: 1, delayMs: 3000 },
  } as const;

  export const COUNTDOWN_SECONDS = 3;
  ```

- [ ] 创建 `frontend/src/vite-env.d.ts`
  ```typescript
  /// <reference types="vite/client" />

  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
  ```

- [ ] 创建 `frontend/src/App.tsx` — 状态机骨架
  ```tsx
  import { useState, useCallback } from 'react';
  import { AppState, StyleOption, HistoryItem } from './types';

  function App() {
    const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
    const [photo, setPhoto] = useState<string>('');
    const [styleOptions, setStyleOptions] = useState<StyleOption[]>([]);
    const [selectedOption, setSelectedOption] = useState<StyleOption | null>(null);
    const [posterUrl, setPosterUrl] = useState<string>('');
    const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
    const [error, setError] = useState<string | null>(null);

    const goToHistory = useCallback(() => setAppState(AppState.HISTORY), []);
    const goToCamera = useCallback(() => {
      setPhoto('');
      setStyleOptions([]);
      setSelectedOption(null);
      setPosterUrl('');
      setError(null);
      setAppState(AppState.CAMERA_READY);
    }, []);

    return (
      <div data-state={appState.toLowerCase()} className="w-screen h-screen bg-gray-950 text-white flex items-center justify-center">
        {appState === AppState.CAMERA_READY && (
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-4">Pose Art Generator</h1>
            <p className="text-gray-400">请做出 OK 手势开始拍照</p>
            <button onClick={goToHistory} className="absolute top-4 right-4 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700">
              历史记录
            </button>
          </div>
        )}
        {appState === AppState.HISTORY && (
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">历史记录</h2>
            <button onClick={goToCamera} className="px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700">
              返回
            </button>
          </div>
        )}
        {/* 其他状态占位 */}
        {appState !== AppState.CAMERA_READY && appState !== AppState.HISTORY && (
          <div className="text-center">
            <p className="text-xl">状态: {appState}</p>
            {error && <p className="text-red-400 mt-2">{error}</p>}
            <button onClick={goToCamera} className="mt-4 px-4 py-2 bg-gray-800 rounded-lg hover:bg-gray-700">
              返回摄像头
            </button>
          </div>
        )}
      </div>
    );
  }

  export default App;
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```
  预期输出: `dist/` 生成，无错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/types/ frontend/src/constants/ frontend/src/App.tsx frontend/src/vite-env.d.ts && git commit -m "feat(frontend): TypeScript 类型定义 + 常量 + App 状态机骨架"
  ```

---

## Task 11: 前端 — API 服务层

**目标:** 封装所有 HTTP 请求（analyze / generate / history），包含统一错误处理和重试策略。

**Files:**
- `E:/Project/1505creative_art/frontend/src/services/api.ts`
- `E:/Project/1505creative_art/frontend/src/services/errorHandler.ts`

**Steps:**

- [ ] 创建 `frontend/src/services/errorHandler.ts`
  ```typescript
  export interface ApiErrorResponse {
    code: string;
    message: string;
    retryable: boolean;
  }

  export async function parseApiError(response: Response): Promise<ApiErrorResponse> {
    let code = 'UNKNOWN_ERROR';
    let message = '请求失败';
    let retryable = false;

    if (response.status === 408 || response.status === 504) {
      code = 'TIMEOUT';
      message = '请求超时，请稍后重试';
      retryable = true;
    } else if (response.status === 429) {
      code = 'RATE_LIMITED';
      message = '请求过于频繁，请稍后重试';
      retryable = true;
    } else if (response.status >= 500) {
      code = 'SERVER_ERROR';
      message = '服务器错误，请稍后重试';
      retryable = true;
    } else if (response.status === 400) {
      code = 'BAD_REQUEST';
      message = '请求参数错误';
      retryable = false;
    } else if (response.status === 401 || response.status === 403) {
      code = 'AUTH_ERROR';
      message = '认证失败';
      retryable = false;
    }

    try {
      const body = await response.json();
      if (body.message) message = body.message;
      if (body.code) code = String(body.code);
    } catch {
      // ignore parse error
    }

    return { code, message, retryable };
  }

  export async function withRetry<T>(
    fn: () => Promise<T>,
    config: { maxRetries: number; delayMs: number },
  ): Promise<T> {
    let lastError: unknown;

    for (let attempt = 0; attempt <= config.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error: any) {
        lastError = error;
        if (!error.retryable || attempt >= config.maxRetries) {
          throw error;
        }
        const delay = config.delayMs * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }
  ```

- [ ] 创建 `frontend/src/services/api.ts`
  ```typescript
  import { API_BASE_URL, API_ENDPOINTS, TIMEOUTS } from '../constants';
  import { parseApiError } from './errorHandler';
  import type { AnalyzeResponse, GenerateResponse, HistoryResponse } from '../types';

  export async function analyzePhoto(photoBase64: string): Promise<AnalyzeResponse> {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.ANALYZE}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: photoBase64,
        image_format: 'jpeg',
      }),
      signal: AbortSignal.timeout(TIMEOUTS.ANALYZE_REQUEST),
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }

    const data: AnalyzeResponse = await response.json();

    if (!data.data?.options || !Array.isArray(data.data.options) || data.data.options.length === 0) {
      throw { code: 'INVALID_RESPONSE', message: '后端返回数据格式异常', retryable: true };
    }

    return data;
  }

  export async function generatePoster(
    photoBase64: string,
    prompt: string,
    styleName: string,
  ): Promise<GenerateResponse> {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.GENERATE}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: photoBase64,
        image_format: 'jpeg',
        prompt,
        style_name: styleName,
      }),
      signal: AbortSignal.timeout(TIMEOUTS.GENERATE_REQUEST),
    });

    if (!response.ok) {
      throw await parseApiError(response);
    }

    const data: GenerateResponse = await response.json();

    if (!data.data?.poster_url) {
      throw { code: 'INVALID_RESPONSE', message: '后端未返回图片', retryable: true };
    }

    return data;
  }

  export async function getHistory(page: number = 1, pageSize: number = 20): Promise<HistoryResponse> {
    const response = await fetch(
      `${API_BASE_URL}${API_ENDPOINTS.HISTORY}?page=${page}&page_size=${pageSize}`,
      { signal: AbortSignal.timeout(TIMEOUTS.HISTORY_REQUEST) },
    );

    if (!response.ok) {
      throw await parseApiError(response);
    }

    return response.json();
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```
  预期输出: 无 TypeScript 错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/services/ && git commit -m "feat(frontend): API 服务层 - analyze/generate/history 封装 + 错误处理 + 重试"
  ```

---

## Task 12: 前端 — 通用 UI 组件

**目标:** 实现 LoadingSpinner 和 ErrorDisplay 两个通用组件。

**Files:**
- `E:/Project/1505creative_art/frontend/src/components/LoadingSpinner/LoadingSpinner.tsx`
- `E:/Project/1505creative_art/frontend/src/components/ErrorDisplay/ErrorDisplay.tsx`

**Steps:**

- [ ] 创建 `frontend/src/components/LoadingSpinner/LoadingSpinner.tsx`
  ```tsx
  interface LoadingSpinnerProps {
    text: string;
    size?: 'sm' | 'md' | 'lg';
  }

  const sizeClasses = {
    sm: 'w-8 h-8 border-2',
    md: 'w-12 h-12 border-3',
    lg: 'w-16 h-16 border-4',
  };

  export default function LoadingSpinner({ text, size = 'md' }: LoadingSpinnerProps) {
    return (
      <div className="flex flex-col items-center gap-4">
        <div
          className={`${sizeClasses[size]} border-gray-600 border-t-cyan-400 rounded-full animate-spin`}
        />
        <p className="text-gray-300 text-lg">{text}</p>
      </div>
    );
  }
  ```

- [ ] 创建 `frontend/src/components/ErrorDisplay/ErrorDisplay.tsx`
  ```tsx
  interface ErrorDisplayProps {
    message: string;
    onRetry?: () => void;
    retryText?: string;
  }

  export default function ErrorDisplay({ message, onRetry, retryText = '重试' }: ErrorDisplayProps) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="text-red-400 text-5xl">!</div>
        <p className="text-gray-300 text-lg max-w-md">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors"
          >
            {retryText}
          </button>
        )}
      </div>
    );
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/components/LoadingSpinner/ frontend/src/components/ErrorDisplay/ && git commit -m "feat(frontend): 通用组件 - LoadingSpinner + ErrorDisplay"
  ```

---

## Task 13: 前端 — 手势检测工具函数

**目标:** 实现纯函数版本的手势判定算法（OK 手势 + 张开手掌），便于单元测试。

**Files:**
- `E:/Project/1505creative_art/frontend/src/utils/gestureAlgo.ts`

**Steps:**

- [ ] 创建 `frontend/src/utils/gestureAlgo.ts`（完整代码来自 frontend-spec D.2）
  ```typescript
  export interface GestureResult {
    gesture: 'ok' | 'open_palm' | 'none';
    confidence: number;
  }

  export interface Landmark {
    x: number;
    y: number;
    z?: number;
  }

  const WRIST = 0;
  const THUMB_TIP = 4;
  const INDEX_FINGER_MCP = 5;
  const INDEX_FINGER_PIP = 6;
  const INDEX_FINGER_TIP = 8;
  const MIDDLE_FINGER_TIP = 12;
  const RING_FINGER_TIP = 16;
  const PINKY_TIP = 20;

  function distance(a: Landmark, b: Landmark): number {
    return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + ((a.z || 0) - (b.z || 0)) ** 2);
  }

  function isOkGesture(landmarks: Landmark[]): boolean {
    const thumbTip = landmarks[THUMB_TIP];
    const indexTip = landmarks[INDEX_FINGER_TIP];
    const thumbIndexDist = distance(thumbTip, indexTip);
    const palmSize = distance(landmarks[WRIST], landmarks[INDEX_FINGER_MCP]);
    const normalizedDist = thumbIndexDist / palmSize;

    if (normalizedDist > 0.25) return false;

    const middleExtended = landmarks[MIDDLE_FINGER_TIP].y < landmarks[11].y;
    const ringExtended = landmarks[RING_FINGER_TIP].y < landmarks[14].y;
    const pinkyExtended = landmarks[PINKY_TIP].y < landmarks[18].y;

    return middleExtended && ringExtended && pinkyExtended;
  }

  function isOpenPalm(landmarks: Landmark[]): boolean {
    const isRightHand = landmarks[WRIST].x < landmarks[INDEX_FINGER_MCP].x;
    const thumbExtended = isRightHand
      ? landmarks[THUMB_TIP].x < landmarks[3].x
      : landmarks[THUMB_TIP].x > landmarks[3].x;

    const indexExtended = landmarks[INDEX_FINGER_TIP].y < landmarks[INDEX_FINGER_PIP].y;
    const middleExtended = landmarks[MIDDLE_FINGER_TIP].y < landmarks[11].y;
    const ringExtended = landmarks[RING_FINGER_TIP].y < landmarks[14].y;
    const pinkyExtended = landmarks[PINKY_TIP].y < landmarks[18].y;

    const extendedCount = [thumbExtended, indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;
    return extendedCount >= 4;
  }

  export function detectGesture(landmarks: Landmark[]): GestureResult {
    if (landmarks.length === 0) {
      return { gesture: 'none', confidence: 0 };
    }
    if (isOkGesture(landmarks)) {
      return { gesture: 'ok', confidence: 0.85 };
    }
    if (isOpenPalm(landmarks)) {
      return { gesture: 'open_palm', confidence: 0.85 };
    }
    return { gesture: 'none', confidence: 0 };
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/utils/gestureAlgo.ts && git commit -m "feat(frontend): 手势判定算法 - OK 手势检测 + 张开手掌检测（纯函数）"
  ```

---

## Task 14: 前端 — Canvas 截帧工具

**目标:** 实现从 video 元素截取当前帧并返回 Base64 字符串的工具函数。

**Files:**
- `E:/Project/1505creative_art/frontend/src/utils/canvas.ts`

**Steps:**

- [ ] 创建 `frontend/src/utils/canvas.ts`
  ```typescript
  /**
   * 从 video 元素截取当前帧，返回 JPEG Base64 字符串（不含 data URI 前缀）。
   * 长边缩放到 1536px 以内以控制文件大小。
   */
  export function captureFrame(video: HTMLVideoElement): string {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d')!;

    const maxWidth = 1536;
    const maxHeight = 1536;
    let { videoWidth: vw, videoHeight: vh } = video;

    if (vw > maxHeight || vh > maxWidth) {
      const ratio = Math.min(maxWidth / vw, maxHeight / vh);
      vw = Math.round(vw * ratio);
      vh = Math.round(vh * ratio);
    }

    canvas.width = vw;
    canvas.height = vh;
    ctx.drawImage(video, 0, 0, vw, vh);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    // 移除 data:image/jpeg;base64, 前缀
    return dataUrl.replace(/^data:image\/jpeg;base64,/, '');
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/utils/canvas.ts && git commit -m "feat(frontend): Canvas 截帧工具 - 视频帧捕获 + JPEG Base64 编码"
  ```

---

## Task 15: 前端 — 摄像头 Hook + MediaPipe Hands Hook

**目标:** 实现 useCamera（getUserMedia 封装）和 useMediaPipeHands（手部检测 + 骨架绘制）两个 Hook。

**Files:**
- `E:/Project/1505creative_art/frontend/src/hooks/useCamera.ts`
- `E:/Project/1505creative_art/frontend/src/hooks/useMediaPipeHands.ts`

**Steps:**

- [ ] 创建 `frontend/src/hooks/useCamera.ts`
  ```typescript
  import { useEffect, useRef, useCallback, useState } from 'react';

  export function useCamera() {
    const videoRef = useRef<HTMLVideoElement>(null!);
    const streamRef = useRef<MediaStream | null>(null);
    const [isReady, setIsReady] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const start = useCallback(async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
          setIsReady(true);
          setError(null);
        }
      } catch (err: any) {
        setError(err.message || '无法访问摄像头');
        setIsReady(false);
      }
    }, []);

    const stop = useCallback(() => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
      setIsReady(false);
    }, []);

    useEffect(() => {
      start();
      return () => stop();
    }, [start, stop]);

    return { videoRef, isReady, error, restart: start };
  }
  ```

- [ ] 创建 `frontend/src/hooks/useMediaPipeHands.ts`
  ```typescript
  import { useEffect, useRef, useCallback } from 'react';
  import { Hands, Results } from '@mediapipe/hands';
  import type { Landmark } from '../utils/gestureAlgo';

  interface UseMediaPipeHandsOptions {
    videoRef: React.RefObject<HTMLVideoElement>;
    onResults: (landmarks: Landmark[]) => void;
  }

  export function useMediaPipeHands({ videoRef, onResults }: UseMediaPipeHandsOptions) {
    const canvasRef = useRef<HTMLCanvasElement>(null!);
    const animFrameRef = useRef<number>(0);

    const drawLandmarks = useCallback((canvas: HTMLCanvasElement, landmarks: Landmark[]) => {
      const ctx = canvas.getContext('2d')!;
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);

      // 连接线（绿色）
      const connections = [
        [0,1],[1,2],[2,3],[3,4],
        [0,5],[5,6],[6,7],[7,8],
        [0,9],[9,10],[10,11],[11,12],
        [0,13],[13,14],[14,15],[15,16],
        [0,17],[17,18],[18,19],[19,20],
        [5,9],[9,13],[13,17],
      ];

      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 2;
      for (const [i, j] of connections) {
        ctx.beginPath();
        ctx.moveTo(landmarks[i].x * width, landmarks[i].y * height);
        ctx.lineTo(landmarks[j].x * width, landmarks[j].y * height);
        ctx.stroke();
      }

      // 关键点（红色圆点）
      ctx.fillStyle = '#ff4444';
      for (const lm of landmarks) {
        ctx.beginPath();
        ctx.arc(lm.x * width, lm.y * height, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }, []);

    useEffect(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas) return;

      const hands = new Hands({
        locateFile: (file: string) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        },
      });

      hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5,
      });

      hands.onResults((results: Results) => {
        // 同步 canvas 尺寸
        if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
        }

        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
          const landmarks: Landmark[] = results.multiHandLandmarks[0];
          drawLandmarks(canvas, landmarks);
          onResults(landmarks);
        } else {
          const ctx = canvas.getContext('2d')!;
          ctx.clearRect(0, 0, canvas.width, canvas.height);
          onResults([]);
        }
      });

      const detect = async () => {
        if (video.readyState >= 2) {
          await hands.send({ image: video });
        }
        animFrameRef.current = requestAnimationFrame(detect);
      };

      detect();

      return () => {
        cancelAnimationFrame(animFrameRef.current);
        hands.close();
      };
    }, [videoRef, onResults, drawLandmarks]);

    return { canvasRef };
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -10
  ```
  预期输出: 可能有 MediaPipe 类型警告但无阻断错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/hooks/ && git commit -m "feat(frontend): useCamera Hook + useMediaPipeHands Hook + 骨架绘制"
  ```

---

## Task 16: 前端 — 手势检测 Hook + 倒计时 Hook

**目标:** 实现 useGestureDetector（防抖手势识别）和 useCountdown（倒计时逻辑）。

**Files:**
- `E:/Project/1505creative_art/frontend/src/hooks/useGestureDetector.ts`
- `E:/Project/1505creative_art/frontend/src/hooks/useCountdown.ts`

**Steps:**

- [ ] 创建 `frontend/src/hooks/useGestureDetector.ts`
  ```typescript
  import { useCallback, useRef } from 'react';
  import { detectGesture, type GestureResult, type Landmark } from '../utils/gestureAlgo';
  import type { GestureEvent } from '../types';

  interface UseGestureDetectorOptions {
    onGestureDetected: (event: GestureEvent) => void;
    okHoldFrames?: number;
    palmHoldFrames?: number;
  }

  export function useGestureDetector({
    onGestureDetected,
    okHoldFrames = 8,
    palmHoldFrames = 5,
  }: UseGestureDetectorOptions) {
    const okCounter = useRef(0);
    const palmCounter = useRef(0);
    const lastGesture = useRef<string>('none');

    const processLandmarks = useCallback(
      (landmarks: Landmark[]) => {
        const result: GestureResult = detectGesture(landmarks);

        if (result.gesture === 'ok') {
          okCounter.current += 1;
          palmCounter.current = 0;
          if (okCounter.current >= okHoldFrames && lastGesture.current !== 'ok') {
            lastGesture.current = 'ok';
            onGestureDetected({
              gesture: 'ok',
              confidence: result.confidence,
              detectedAt: Date.now(),
            });
            okCounter.current = 0;
          }
        } else if (result.gesture === 'open_palm') {
          palmCounter.current += 1;
          okCounter.current = 0;
          if (palmCounter.current >= palmHoldFrames && lastGesture.current !== 'open_palm') {
            lastGesture.current = 'open_palm';
            onGestureDetected({
              gesture: 'open_palm',
              confidence: result.confidence,
              detectedAt: Date.now(),
            });
            palmCounter.current = 0;
          }
        } else {
          okCounter.current = 0;
          palmCounter.current = 0;
          if (lastGesture.current !== 'none') {
            lastGesture.current = 'none';
          }
        }
      },
      [onGestureDetected, okHoldFrames, palmHoldFrames],
    );

    return { processLandmarks };
  }
  ```

- [ ] 创建 `frontend/src/hooks/useCountdown.ts`
  ```typescript
  import { useState, useEffect, useRef, useCallback } from 'react';

  interface UseCountdownOptions {
    seconds: number;
    onComplete: () => void;
    active: boolean;
  }

  export function useCountdown({ seconds, onComplete, active }: UseCountdownOptions) {
    const [remaining, setRemaining] = useState(seconds);
    const intervalRef = useRef<number | null>(null);
    const onCompleteRef = useRef(onComplete);
    onCompleteRef.current = onComplete;

    const reset = useCallback(() => {
      setRemaining(seconds);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }, [seconds]);

    useEffect(() => {
      if (!active) {
        reset();
        return;
      }

      intervalRef.current = window.setInterval(() => {
        setRemaining((prev) => {
          if (prev <= 1) {
            if (intervalRef.current) clearInterval(intervalRef.current);
            onCompleteRef.current();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
      };
    }, [active, reset]);

    return { remaining, reset };
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/hooks/useGestureDetector.ts frontend/src/hooks/useCountdown.ts && git commit -m "feat(frontend): useGestureDetector Hook（防抖） + useCountdown Hook"
  ```

---

## Task 17: 前端 — CameraView + GestureOverlay + Countdown 组件

**目标:** 实现摄像头视图组件、手势状态提示浮层和倒计时动画组件。

**Files:**
- `E:/Project/1505creative_art/frontend/src/components/CameraView/CameraView.tsx`
- `E:/Project/1505creative_art/frontend/src/components/GestureOverlay/GestureOverlay.tsx`
- `E:/Project/1505creative_art/frontend/src/components/Countdown/Countdown.tsx`

**Steps:**

- [ ] 创建 `frontend/src/components/CameraView/CameraView.tsx`
  ```tsx
  import type { Landmark } from '../../utils/gestureAlgo';

  interface CameraViewProps {
    videoRef: React.RefObject<HTMLVideoElement>;
    canvasRef: React.RefObject<HTMLCanvasElement>;
    landmarks: Landmark[] | null;
    onError?: (error: Error) => void;
  }

  export default function CameraView({ videoRef, canvasRef }: CameraViewProps) {
    return (
      <div className="relative w-full h-full flex items-center justify-center bg-black">
        <video
          ref={videoRef}
          className="max-w-full max-h-full object-cover"
          playsInline
          muted
        />
        <canvas
          ref={canvasRef}
          className="absolute top-0 left-0 w-full h-full pointer-events-none"
        />
      </div>
    );
  }
  ```

- [ ] 创建 `frontend/src/components/GestureOverlay/GestureOverlay.tsx`
  ```tsx
  import type { GestureType } from '../../types';

  interface GestureOverlayProps {
    gesture: GestureType;
    isGestureDetected: boolean;
    hintText: string;
  }

  export default function GestureOverlay({ gesture, isGestureDetected, hintText }: GestureOverlayProps) {
    return (
      <div className="absolute bottom-0 left-0 right-0 p-6 text-center pointer-events-none">
        <div
          className={`inline-block px-6 py-3 rounded-full backdrop-blur-md transition-all duration-300 ${
            isGestureDetected
              ? 'bg-green-500/30 border-2 border-green-400 shadow-lg shadow-green-500/20'
              : 'bg-gray-800/60 border-2 border-gray-600'
          }`}
        >
          <p className="text-white text-lg font-medium">{hintText}</p>
          {gesture === 'ok' && (
            <p className="text-green-300 text-sm mt-1">OK 手势已识别!</p>
          )}
        </div>
      </div>
    );
  }
  ```

- [ ] 创建 `frontend/src/components/Countdown/Countdown.tsx`
  ```tsx
  interface CountdownProps {
    remaining: number;
  }

  export default function Countdown({ remaining }: CountdownProps) {
    if (remaining <= 0) return null;

    return (
      <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
        <div
          key={remaining}
          className="text-[120px] font-bold text-white animate-pulse drop-shadow-2xl"
          style={{
            textShadow: '0 0 40px rgba(0, 200, 255, 0.5)',
          }}
        >
          {remaining}
        </div>
      </div>
    );
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/components/CameraView/ frontend/src/components/GestureOverlay/ frontend/src/components/Countdown/ && git commit -m "feat(frontend): CameraView + GestureOverlay + Countdown 组件"
  ```

---

## Task 18: 前端 — StyleCard + StyleSelection 组件

**目标:** 实现风格选项卡片和风格选择面板组件。

**Files:**
- `E:/Project/1505creative_art/frontend/src/components/StyleCard/StyleCard.tsx`
- `E:/Project/1505creative_art/frontend/src/components/StyleSelection/StyleSelection.tsx`

**Steps:**

- [ ] 创建 `frontend/src/components/StyleCard/StyleCard.tsx`
  ```tsx
  import type { StyleOption } from '../../types';

  interface StyleCardProps {
    option: StyleOption;
    index: number;
    onSelect: (option: StyleOption) => void;
    isSelected: boolean;
  }

  export default function StyleCard({ option, index, onSelect, isSelected }: StyleCardProps) {
    return (
      <button
        onClick={() => onSelect(option)}
        className={`relative p-6 rounded-xl border-2 text-left transition-all duration-300 hover:scale-105 hover:shadow-xl cursor-pointer
          ${isSelected
            ? 'border-cyan-400 bg-cyan-500/10 shadow-lg shadow-cyan-500/20'
            : 'border-gray-700 bg-gray-800/50 hover:border-gray-500'
          }`}
        style={{ animationDelay: `${index * 150}ms` }}
      >
        <h3 className="text-xl font-bold text-white mb-2">{option.name}</h3>
        <p className="text-gray-400 text-sm">{option.brief}</p>
        {isSelected && (
          <div className="absolute top-3 right-3 w-6 h-6 rounded-full bg-cyan-400 flex items-center justify-center">
            <svg className="w-4 h-4 text-gray-900" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        )}
      </button>
    );
  }
  ```

- [ ] 创建 `frontend/src/components/StyleSelection/StyleSelection.tsx`
  ```tsx
  import type { StyleOption } from '../../types';
  import StyleCard from '../StyleCard/StyleCard';
  import LoadingSpinner from '../LoadingSpinner/LoadingSpinner';
  import ErrorDisplay from '../ErrorDisplay/ErrorDisplay';

  interface StyleSelectionProps {
    options: StyleOption[];
    onSelect: (option: StyleOption) => void;
    isLoading: boolean;
    error: string | null;
    onRetry: () => void;
    photoUrl?: string;
  }

  export default function StyleSelection({
    options,
    onSelect,
    isLoading,
    error,
    onRetry,
    photoUrl,
  }: StyleSelectionProps) {
    if (isLoading) {
      return <LoadingSpinner text="AI 正在分析你的姿势..." />;
    }

    if (error) {
      return <ErrorDisplay message={error} onRetry={onRetry} />;
    }

    return (
      <div className="w-full max-w-4xl px-6">
        {photoUrl && (
          <img
            src={`data:image/jpeg;base64,${photoUrl}`}
            alt="已拍摄照片"
            className="w-24 h-24 rounded-lg object-cover mb-6 border border-gray-700"
          />
        )}
        <h2 className="text-2xl font-bold text-white mb-6">选择你喜欢的风格</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {options.map((option, index) => (
            <StyleCard
              key={option.name}
              option={option}
              index={index}
              onSelect={onSelect}
              isSelected={false}
            />
          ))}
        </div>
      </div>
    );
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/components/StyleCard/ frontend/src/components/StyleSelection/ && git commit -m "feat(frontend): StyleCard + StyleSelection 组件"
  ```

---

## Task 19: 前端 — PosterDisplay + HistoryList 组件

**目标:** 实现海报展示组件（含下载功能）和历史记录列表组件。

**Files:**
- `E:/Project/1505creative_art/frontend/src/components/PosterDisplay/PosterDisplay.tsx`
- `E:/Project/1505creative_art/frontend/src/components/HistoryList/HistoryList.tsx`

**Steps:**

- [ ] 创建 `frontend/src/components/PosterDisplay/PosterDisplay.tsx`
  ```tsx
  import { API_BASE_URL } from '../../constants';

  interface PosterDisplayProps {
    posterUrl: string;
    styleName: string;
    onDownload: () => void;
    onRegenerate: () => void;
    onRetake: () => void;
    onViewHistory: () => void;
  }

  export default function PosterDisplay({
    posterUrl,
    styleName,
    onDownload,
    onRegenerate,
    onRetake,
    onViewHistory,
  }: PosterDisplayProps) {
    const fullUrl = posterUrl.startsWith('data:') ? posterUrl : `${API_BASE_URL}${posterUrl}`;

    return (
      <div className="w-full max-w-2xl px-6 text-center">
        <p className="text-gray-400 mb-4">风格: {styleName}</p>
        <img
          src={fullUrl}
          alt="生成的艺术海报"
          className="w-full max-h-[70vh] rounded-xl shadow-2xl border border-gray-800"
        />
        <div className="flex gap-3 justify-center mt-6">
          <button
            onClick={onDownload}
            className="px-5 py-2.5 bg-cyan-600 hover:bg-cyan-500 rounded-lg transition-colors font-medium"
          >
            保存海报
          </button>
          <button
            onClick={onRegenerate}
            className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            重新生成
          </button>
          <button
            onClick={onRetake}
            className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            重新拍照
          </button>
          <button
            onClick={onViewHistory}
            className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            历史记录
          </button>
        </div>
      </div>
    );
  }
  ```

- [ ] 创建 `frontend/src/components/HistoryList/HistoryList.tsx`
  ```tsx
  import { API_BASE_URL } from '../../constants';
  import type { HistoryItem } from '../../types';
  import LoadingSpinner from '../LoadingSpinner/LoadingSpinner';

  interface HistoryListProps {
    items: HistoryItem[];
    isLoading: boolean;
    onBack: () => void;
  }

  function formatDate(isoStr: string): string {
    try {
      return new Date(isoStr).toLocaleString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  }

  export default function HistoryList({ items, isLoading, onBack }: HistoryListProps) {
    if (isLoading) {
      return <LoadingSpinner text="加载历史记录..." />;
    }

    return (
      <div className="w-full max-w-4xl px-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-white">历史记录</h2>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            返回摄像头
          </button>
        </div>

        {items.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-500 text-lg">暂无历史记录</p>
            <p className="text-gray-600 text-sm mt-2">拍照生成你的第一张艺术海报吧!</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {items.map((item) => {
              const thumbUrl = item.thumbnail_url
                ? (item.thumbnail_url.startsWith('data:') ? item.thumbnail_url : `${API_BASE_URL}${item.thumbnail_url}`)
                : '';
              return (
                <div key={item.id} className="bg-gray-800/50 rounded-lg overflow-hidden border border-gray-700">
                  {thumbUrl ? (
                    <img
                      src={thumbUrl}
                      alt={item.style_name}
                      className="w-full aspect-square object-cover"
                    />
                  ) : (
                    <div className="w-full aspect-square bg-gray-800 flex items-center justify-center text-gray-600">
                      无预览
                    </div>
                  )}
                  <div className="p-3">
                    <p className="text-white text-sm font-medium truncate">{item.style_name}</p>
                    <p className="text-gray-500 text-xs mt-1">{formatDate(item.created_at)}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
  ```

- [ ] 验证前端构建
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1 | tail -5
  ```

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/components/PosterDisplay/ frontend/src/components/HistoryList/ && git commit -m "feat(frontend): PosterDisplay（含下载） + HistoryList 组件"
  ```

---

## Task 20: 前端 — App.tsx 完整状态机集成

**目标:** 将所有组件和 Hook 集成到 App.tsx 状态机中，实现完整的用户流程。

**Files:**
- `E:/Project/1505creative_art/frontend/src/App.tsx`
- `E:/Project/1505creative_art/frontend/src/main.tsx`

**Steps:**

- [ ] 重写 `frontend/src/App.tsx` — 完整状态机集成
  ```tsx
  import { useState, useCallback, useRef } from 'react';
  import { AppState, type StyleOption, type HistoryItem, type GestureEvent, type Landmark } from './types';
  import { useCamera } from './hooks/useCamera';
  import { useMediaPipeHands } from './hooks/useMediaPipeHands';
  import { useGestureDetector } from './hooks/useGestureDetector';
  import { useCountdown } from './hooks/useCountdown';
  import { captureFrame } from './utils/canvas';
  import { analyzePhoto, generatePoster, getHistory } from './services/api';
  import { withRetry } from './services/errorHandler';
  import { RETRY_CONFIG } from './constants';

  import CameraView from './components/CameraView/CameraView';
  import GestureOverlay from './components/GestureOverlay/GestureOverlay';
  import CountdownComponent from './components/Countdown/Countdown';
  import StyleSelection from './components/StyleSelection/StyleSelection';
  import PosterDisplay from './components/PosterDisplay/PosterDisplay';
  import HistoryList from './components/HistoryList/HistoryList';
  import LoadingSpinner from './components/LoadingSpinner/LoadingSpinner';
  import ErrorDisplay from './components/ErrorDisplay/ErrorDisplay';

  function App() {
    const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
    const [photo, setPhoto] = useState<string>('');
    const [styleOptions, setStyleOptions] = useState<StyleOption[]>([]);
    const [selectedOption, setSelectedOption] = useState<StyleOption | null>(null);
    const [posterUrl, setPosterUrl] = useState<string>('');
    const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [gesture, setGesture] = useState<'ok' | 'open_palm' | 'none'>('none');
    const [historyLoading, setHistoryLoading] = useState(false);

    const { videoRef, isReady: cameraReady, error: cameraError } = useCamera();

    const handleGestureDetected = useCallback((event: GestureEvent) => {
      setGesture(event.gesture);
      if (event.gesture === 'ok' && appState === AppState.CAMERA_READY) {
        setAppState(AppState.COUNTDOWN);
      } else if (event.gesture === 'open_palm' && appState !== AppState.POSTER_READY) {
        setAppState(AppState.CAMERA_READY);
        setError(null);
      }
    }, [appState]);

    const gestureDetector = useGestureDetector({
      onGestureDetected: handleGestureDetected,
    });

    const handleMediaPipeResults = useCallback((landmarks: Landmark[]) => {
      gestureDetector.processLandmarks(landmarks);
    }, [gestureDetector]);

    const { canvasRef } = useMediaPipeHands({
      videoRef,
      onResults: handleMediaPipeResults,
    });

    const handleCountdownComplete = useCallback(() => {
      const base64 = captureFrame(videoRef.current);
      setPhoto(base64);
      setAppState(AppState.ANALYZING);
      setError(null);

      withRetry(
        () => analyzePhoto(base64),
        RETRY_CONFIG.ANALYZE,
      )
        .then((result) => {
          setStyleOptions(result.data.options);
          setAppState(AppState.STYLE_SELECTION);
        })
        .catch((err: any) => {
          setError(err.message || '分析失败，请重试');
        });
    }, [videoRef]);

    const { remaining: countdownRemaining } = useCountdown({
      seconds: 3,
      onComplete: handleCountdownComplete,
      active: appState === AppState.COUNTDOWN,
    });

    const handleStyleSelect = useCallback(async (option: StyleOption) => {
      setSelectedOption(option);
      setAppState(AppState.GENERATING);
      setError(null);

      withRetry(
        () => generatePoster(photo, option.prompt, option.name),
        RETRY_CONFIG.GENERATE,
      )
        .then((result) => {
          setPosterUrl(result.data.poster_url);
          setAppState(AppState.POSTER_READY);
        })
        .catch((err: any) => {
          setError(err.message || '生成失败，请重试');
        });
    }, [photo]);

    const handleDownload = useCallback(() => {
      const url = posterUrl.startsWith('data:') ? posterUrl : posterUrl;
      if (url.startsWith('data:')) {
        const link = document.createElement('a');
        link.href = url;
        link.download = `pose-art-${Date.now()}.png`;
        link.click();
      } else {
        window.open(url, '_blank');
      }
    }, [posterUrl]);

    const handleRegenerate = useCallback(() => {
      if (selectedOption) {
        handleStyleSelect(selectedOption);
      }
    }, [selectedOption, handleStyleSelect]);

    const goToCamera = useCallback(() => {
      setPhoto('');
      setStyleOptions([]);
      setSelectedOption(null);
      setPosterUrl('');
      setError(null);
      setGesture('none');
      setAppState(AppState.CAMERA_READY);
    }, []);

    const goToHistory = useCallback(async () => {
      setAppState(AppState.HISTORY);
      setHistoryLoading(true);
      try {
        const resp = await getHistory();
        setHistoryItems(resp.data.items);
      } catch {
        setHistoryItems([]);
      } finally {
        setHistoryLoading(false);
      }
    }, []);

    const handleRetry = useCallback(() => {
      if (appState === AppState.ANALYZING && photo) {
        setError(null);
        withRetry(() => analyzePhoto(photo), RETRY_CONFIG.ANALYZE)
          .then((result) => {
            setStyleOptions(result.data.options);
            setAppState(AppState.STYLE_SELECTION);
          })
          .catch((err: any) => setError(err.message || '分析失败'));
      } else if (appState === AppState.GENERATING && selectedOption) {
        setError(null);
        handleStyleSelect(selectedOption);
      }
    }, [appState, photo, selectedOption, handleStyleSelect]);

    // 摄像头错误
    if (cameraError) {
      return (
        <div className="w-screen h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-center">
            <p className="text-red-400 text-xl mb-4">摄像头访问失败</p>
            <p className="text-gray-400 mb-6">{cameraError}</p>
            <button onClick={() => window.location.reload()} className="px-4 py-2 bg-cyan-600 rounded-lg">
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return (
      <div data-state={appState.toLowerCase()} className="w-screen h-screen bg-gray-950 text-white flex items-center justify-center relative overflow-hidden">
        {/* 历史记录按钮（仅在 CAMERA_READY 时显示） */}
        {appState === AppState.CAMERA_READY && (
          <button
            onClick={goToHistory}
            className="absolute top-4 right-4 z-30 px-4 py-2 bg-gray-800/80 rounded-lg hover:bg-gray-700 transition-colors backdrop-blur-sm"
          >
            历史记录
          </button>
        )}

        {/* CAMERA_READY / COUNTDOWN — 摄像头画面 */}
        {(appState === AppState.CAMERA_READY || appState === AppState.COUNTDOWN) && (
          <>
            <CameraView videoRef={videoRef} canvasRef={canvasRef} landmarks={null} />
            {appState === AppState.COUNTDOWN && (
              <CountdownComponent remaining={countdownRemaining} />
            )}
            <GestureOverlay
              gesture={gesture}
              isGestureDetected={gesture === 'ok'}
              hintText={appState === AppState.COUNTDOWN ? '张开手掌取消' : '请做出 OK 手势开始拍照'}
            />
          </>
        )}

        {/* ANALYZING — 分析中 */}
        {appState === AppState.ANALYZING && (
          <div className="flex flex-col items-center gap-6">
            {photo && (
              <img
                src={`data:image/jpeg;base64,${photo}`}
                alt="已拍摄"
                className="w-48 h-48 rounded-xl object-cover border border-gray-700"
              />
            )}
            {error ? (
              <ErrorDisplay message={error} onRetry={handleRetry} />
            ) : (
              <LoadingSpinner text="AI 正在分析你的姿势..." />
            )}
          </div>
        )}

        {/* STYLE_SELECTION — 风格选择 */}
        {appState === AppState.STYLE_SELECTION && (
          <StyleSelection
            options={styleOptions}
            onSelect={handleStyleSelect}
            isLoading={false}
            error={error}
            onRetry={handleRetry}
            photoUrl={photo}
          />
        )}

        {/* GENERATING — 生成中 */}
        {appState === AppState.GENERATING && (
          <div className="flex flex-col items-center gap-6">
            {selectedOption && (
              <p className="text-gray-400">正在生成: {selectedOption.name}</p>
            )}
            {error ? (
              <ErrorDisplay message={error} onRetry={handleRetry} />
            ) : (
              <LoadingSpinner text="AI 正在生成艺术海报..." size="lg" />
            )}
          </div>
        )}

        {/* POSTER_READY — 海报展示 */}
        {appState === AppState.POSTER_READY && (
          <PosterDisplay
            posterUrl={posterUrl}
            styleName={selectedOption?.name || ''}
            onDownload={handleDownload}
            onRegenerate={handleRegenerate}
            onRetake={goToCamera}
            onViewHistory={goToHistory}
          />
        )}

        {/* HISTORY — 历史记录 */}
        {appState === AppState.HISTORY && (
          <HistoryList
            items={historyItems}
            isLoading={historyLoading}
            onBack={goToCamera}
          />
        )}
      </div>
    );
  }

  export default App;
  ```

- [ ] 更新 `frontend/src/main.tsx`
  ```tsx
  import React from 'react';
  import ReactDOM from 'react-dom/client';
  import App from './App';
  import './index.css';

  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
  ```

- [ ] 验证前端构建（完整集成后可能有非阻断警告）
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build 2>&1
  ```
  预期输出: `dist/` 生成，无阻断性错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add frontend/src/App.tsx frontend/src/main.tsx && git commit -m "feat(frontend): App.tsx 完整状态机集成 — 所有组件和 Hook 串联"
  ```

---

## Task 21: 端到端联调 + 验收

**目标:** 启动前后端，完整走通用户流程，验证所有功能。

**Files:** 无新文件，仅验证。

**Steps:**

- [ ] 启动后端服务
  ```bash
  cd E:/Project/1505creative_art/backend && python run.py
  ```
  预期输出: `Uvicorn running on http://0.0.0.0:8000`

- [ ] 验证后端 health 接口
  ```bash
  curl http://localhost:8000/health
  ```
  预期输出: `{"status":"ok","app":"PoseArtGenerator"}`

- [ ] 验证后端 Swagger UI
  ```bash
  curl -s http://localhost:8000/docs | head -5
  ```
  预期输出: HTML 页面（Swagger UI）

- [ ] 启动前端开发服务器
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run dev
  ```
  预期输出: `Local: http://localhost:5173`

- [ ] 在浏览器打开 `http://localhost:5173` 验证:
  - 页面显示 "Pose Art Generator" 和 "请做出 OK 手势开始拍照"
  - 允许摄像头权限后显示实时视频画面
  - 右上角有"历史记录"按钮

- [ ] 运行所有后端测试
  ```bash
  cd E:/Project/1505creative_art/backend && python -m pytest tests/ -v --tb=short
  ```
  预期输出: 所有测试 PASS

- [ ] 前端生产构建验证
  ```bash
  cd E:/Project/1505creative_art/frontend && npm run build && ls dist/
  ```
  预期输出: `dist/index.html`, `dist/assets/...` 无错误

- [ ] Commit
  ```bash
  cd E:/Project/1505creative_art && git add -A && git commit -m "chore: 端到端联调验证通过"
  ```

---

## 总结

### 任务依赖关系图

```
Task 1 (项目初始化)
  ├── Task 2 (后端配置)
  │     ├── Task 3 (Schema 定义)
  │     │     ├── Task 4 (Vision LLM 客户端)
  │     │     ├── Task 5 (Qwen Image 客户端)
  │     │     └── Task 6 (系统提示词 + 文件存储)
  │     │           ├── Task 7 (/api/analyze)
  │     │           │     └── Task 8 (/api/generate + /api/history)
  │     │           │           └── Task 9 (测试补全)
  │     │           └──
  │     └──
  └── Task 10 (前端类型+骨架)
        ├── Task 11 (API 服务层)
        ├── Task 12 (通用组件)
        ├── Task 13 (手势算法)
        ├── Task 14 (Canvas 工具)
        ├── Task 15 (Camera + MediaPipe Hooks)
        ├── Task 16 (GestureDetector + Countdown Hooks)
        ├── Task 17 (CameraView + GestureOverlay + Countdown)
        ├── Task 18 (StyleCard + StyleSelection)
        └── Task 19 (PosterDisplay + HistoryList)
              └── Task 20 (App 完整集成)
                    └── Task 21 (端到端联调)
```

### 后端可独立验证

Task 1-9（后端全部）可以独立于前端完成并验证，通过 `pytest` 和 `curl` 测试。

### 前端可独立开发

Task 10-20（前端全部）可以在没有真实后端的情况下开发和构建，通过 `npm run build` 验证 TypeScript 编译。

### 最终验收清单

- [ ] 后端所有 pytest 测试通过
- [ ] 前端 `npm run build` 无错误
- [ ] `/health` 接口返回正常
- [ ] `/docs` Swagger UI 可访问
- [ ] 浏览器打开前端页面无白屏
- [ ] 摄像头权限正常请求和显示
- [ ] 完整用户流程可走通（需真实 API Key）

