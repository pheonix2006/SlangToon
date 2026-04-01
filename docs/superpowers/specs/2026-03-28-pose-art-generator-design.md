# Pose Art Generator — Design Spec

## Overview

交互式艺术 Web 应用：用户站在摄像头前，做出 OK 手势触发拍照，视觉 LLM 分析照片生成多个创意风格选项，用户选择后调用 Qwen Image 2.0 生成艺术海报。

## Architecture

**前后端分离**，前端负责摄像头采集和 UI 交互，后端负责 AI API 调用。

```
Frontend (React + TS + Vite + Tailwind)
  │
  ├─ Camera Module: getUserMedia 实时视频流
  ├─ MediaPipe Hands: 浏览器端手部关键点检测
  └─ UI: 倒计时 / 风格选择 / 海报展示 / 历史记录
  │
  │  HTTP REST API
  ▼
Backend (Python FastAPI)
  │
  ├─ POST /api/analyze      — 照片 → Vision LLM → 风格选项
  ├─ POST /api/generate      — 照片 + prompt → Qwen Image 2.0 → 海报
  └─ GET  /api/history       — 历史记录
  │
  ├─ Vision LLM (OpenAI-compatible API, 可配置 URL/Key)
  └─ Qwen Image 2.0 (图像生成)
```

## Core Flow (MVP)

1. **摄像头等待** — 显示实时画面 + 手部骨架叠加，检测 OK 手势
2. **3 秒倒计时** — 屏幕显示倒计时数字，张开手掌可取消
3. **拍照** — Canvas 截取当前帧，Base64 编码
4. **发送到后端** — POST /api/analyze，附带照片
5. **视觉模型分析** — 后端调用 Vision LLM（系统提示词 + 用户照片），返回 3 个风格选项
6. **用户选择风格** — 前端展示风格卡片，用户点击选择（MVP 用按钮）
7. **生成海报** — POST /api/generate，附带照片 + 选中的详细 prompt
8. **展示结果** — 海报展示 + 保存下载 / 重新生成 / 重新拍照 / 历史记录

## Prompt Pipeline

### Stage 1: System Prompt (预定义，可配置)

角色设定 + 风格方向池 + 输出格式要求 + 生图提示词写作规范。

视觉模型收到的输入：
- 系统提示词（包含角色、风格池、输出 JSON schema、提示词写作规范）
- 用户消息：base64 图片 + "请分析照片中的人物，生成 3 个创意风格选项"

### Stage 2: Vision LLM 输出格式

```json
{
  "options": [
    {
      "name": "风格名称",
      "brief": "给用户看的简略描述（一句话）",
      "prompt": "给生图模型的详细提示词（构图/光影/色彩/人物细节/场景氛围/镜头角度）"
    }
  ]
}
```

### Stage 3: 用户选择

前端展示 `name` + `brief`，用户点击选择。

### Stage 4: Qwen Image 2.0

用户照片 + 选中的 `prompt` → 图生图模式 → 海报。

## Tech Stack

| Layer | Choice |
|-------|--------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Hand Detection | MediaPipe Hands (@mediapipe/hands) |
| Backend | Python 3.11+ + FastAPI + Uvicorn |
| LLM Client | OpenAI-compatible HTTP client (可配置 base_url + api_key) |
| Image Gen | Qwen Image 2.0 API |
| Config | .env file |

## MVP Gesture Scope

| Gesture | Action | Context |
|---------|--------|---------|
| OK sign | 触发拍照 | 摄像头模式 |
| Open palm | 取消/返回 | 任意状态 |
| (buttons) | 风格选择/确认/保存等 | MVP 用按钮，后续替换为手势 |

## Out of Scope (MVP)

- 多手势识别（OK 以外的手势后续迭代）
- 用户管理 / 登录
- 海报模板编辑
- 移动端适配
- 性能优化（模型缓存、CDN 等）
