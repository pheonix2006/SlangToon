# Pose Art Generator — 前端规格文档

> 版本：1.0.0
> 日期：2026-03-28
> 技术栈：React 18 + TypeScript + Vite + Tailwind CSS + @mediapipe/hands

---

## A. 项目结构

### A.1 目录结构设计

```
pose-art-generator/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── .env                          # 前端环境变量（API_BASE_URL 等）
├── public/
│   ├── favicon.ico
│   └── sounds/
│       └── countdown-beep.mp3    # 倒计时提示音效
└── src/
    ├── main.tsx                  # React 应用入口
    ├── App.tsx                   # 根组件，状态机宿主
    ├── index.css                 # Tailwind 指令 + 全局样式
    ├── vite-env.d.ts             # Vite 类型声明
    │
    ├── types/
    │   └── index.ts              # 全局 TypeScript 类型定义
    │
    ├── constants/
    │   └── index.ts              # 常量定义（API 路径、超时时间、倒计时秒数等）
    │
    ├── hooks/
    │   ├── useCamera.ts          # 摄像头生命周期管理 hook
    │   ├── useMediaPipeHands.ts  # MediaPipe Hands 初始化与帧处理 hook
    │   ├── useGestureDetector.ts # 手势识别逻辑 hook（OK 手势 + 张开手掌）
    │   └── useCountdown.ts       # 倒计时逻辑 hook
    │
    ├── services/
    │   ├── api.ts                # HTTP 请求封装（analyze / generate / history）
    │   └── errorHandler.ts       # 统一错误处理与重试策略
    │
    ├── components/
    │   ├── CameraView/
    │   │   ├── CameraView.tsx            # 摄像头视频流 + Canvas 骨架叠加
    │   │   └── CameraView.module.css     # 组件局部样式（如有）
    │   │
    │   ├── GestureOverlay/
    │   │   ├── GestureOverlay.tsx        # 手势识别状态提示浮层
    │   │   └── GestureOverlay.module.css
    │   │
    │   ├── Countdown/
    │   │   ├── Countdown.tsx             # 倒计时动画组件
    │   │   └── Countdown.module.css
    │   │
    │   ├── StyleCard/
    │   │   ├── StyleCard.tsx             # 单个风格选项卡片
    │   │   └── StyleCard.module.css
    │   │
    │   ├── StyleSelection/
    │   │   └── StyleSelection.tsx        # 风格选择面板（包含多个 StyleCard）
    │   │
    │   ├── PosterDisplay/
    │   │   ├── PosterDisplay.tsx         # 生成结果展示 + 操作按钮
    │   │   └── PosterDisplay.module.css
    │   │
    │   ├── HistoryList/
    │   │   ├── HistoryList.tsx           # 历史记录列表
    │   │   └── HistoryList.module.css
    │   │
    │   ├── LoadingSpinner/
    │   │   └── LoadingSpinner.tsx        # 通用加载动画
    │   │
    │   └── ErrorDisplay/
    │       └── ErrorDisplay.tsx          # 通用错误提示 + 重试按钮
    │
    └── utils/
        ├── canvas.ts             # Canvas 截帧与 Base64 编码工具
        └── gestureAlgo.ts        # 手势判定纯函数（供测试使用）
```

### A.2 关键文件清单与职责说明

| 文件 | 职责 |
|------|------|
| `src/App.tsx` | 顶层状态机，管理 AppState 并根据当前状态渲染对应 UI |
| `src/types/index.ts` | 所有共享 TypeScript 接口/类型定义 |
| `src/hooks/useCamera.ts` | 封装 `navigator.mediaDevices.getUserMedia`，管理视频流的生命周期（开启/关闭/切换前后置） |
| `src/hooks/useMediaPipeHands.ts` | 初始化 @mediapipe/hands，逐帧送入视频进行手部关键点检测，输出 landmarks |
| `src/hooks/useGestureDetector.ts` | 接收 landmarks，判定 OK 手势或张开手掌，触发回调 |
| `src/hooks/useCountdown.ts` | 管理 3 秒倒计时，支持取消 |
| `src/services/api.ts` | 封装所有 HTTP 请求（`analyze`、`generate`、`getHistory`） |
| `src/services/errorHandler.ts` | 网络错误分类、超时处理、自动重试策略 |
| `src/components/CameraView/CameraView.tsx` | 渲染 `<video>` + `<canvas>` 叠加层，实时绘制手部骨架 |
| `src/utils/gestureAlgo.ts` | 纯函数：接收 landmarks 数组，返回 `{ gesture: 'ok' \| 'open_palm' \| 'none' }` |
| `src/utils/canvas.ts` | 纯函数：从 video 元素截取当前帧并返回 Base64 字符串 |

---

## B. 页面/状态设计

### B.1 状态枚举定义

```typescript
export enum AppState {
  CAMERA_READY     = 'CAMERA_READY',      // 摄像头就绪，等待用户做出 OK 手势
  COUNTDOWN        = 'COUNTDOWN',          // 3 秒倒计时进行中
  PHOTO_TAKEN      = 'PHOTO_TAKEN',        // 照片已截取，准备发送分析请求
  ANALYZING        = 'ANALYZING',          // 后端正在分析照片
  STYLE_SELECTION  = 'STYLE_SELECTION',    // 用户选择创意风格
  GENERATING       = 'GENERATING',         // 后端正在生成海报
  POSTER_READY     = 'POSTER_READY',       // 海报生成完成，展示结果
  HISTORY          = 'HISTORY',            // 查看历史记录
}
```

### B.2 各状态的 UI 组件与可见元素

#### CAMERA_READY

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| CameraView | 组件 | 可见 | 全屏摄像头画面 + 手部骨架叠加 |
| GestureOverlay | 组件 | 可见 | 提示文字"请做出 OK 手势开始拍照"，检测到手势时变为高亮 |
| 历史记录按钮 | 按钮 | 可见 | 右上角，导航到 HISTORY 状态 |

#### COUNTDOWN

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| CameraView | 组件 | 可见 | 保持摄像头画面（冻结最后一帧可选） |
| Countdown | 组件 | 可见 | 居中大数字 3 → 2 → 1，带缩放动画 + 音效 |
| GestureOverlay | 组件 | 可见 | 提示"张开手掌取消" |
| 音效 | 媒体 | 可见 | 每秒播放一次 beep 音效 |

#### PHOTO_TAKEN

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| 照片缩略图 | 图片 | 可见 | 居中显示已拍摄的照片 |
| LoadingSpinner | 组件 | 可见 | 显示"正在分析照片..."文字 |
| （此状态持续时间极短，可合并到 ANALYZING） |

#### ANALYZING

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| 照片缩略图 | 图片 | 可见 | 左侧或顶部显示已拍摄照片 |
| LoadingSpinner | 组件 | 可见 | 居中加载动画 + 文字"AI 正在分析你的姿势..." |
| ErrorDisplay | 组件 | 条件可见 | 分析失败时显示错误信息和重试按钮 |

#### STYLE_SELECTION

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| 照片缩略图 | 图片 | 可见 | 顶部/左侧小图 |
| StyleSelection | 组件 | 可见 | 展示 3 张 StyleCard |
| 每张 StyleCard | 组件 | 可见 | 风格名称 + 一句话描述 |
| ErrorDisplay | 组件 | 条件可见 | 分析返回异常时显示 |

#### GENERATING

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| 选中风格信息 | 文本 | 可见 | 显示用户选择的风格名称 |
| LoadingSpinner | 组件 | 可见 | 居中加载动画 + 文字"AI 正在生成艺术海报..." |
| 进度提示 | 文本 | 可见 | 可选：模拟进度条或阶段提示 |

#### POSTER_READY

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| PosterDisplay | 组件 | 可见 | 展示生成的海报图片（大图） |
| 保存/下载按钮 | 按钮 | 可见 | 下载海报到本地 |
| 重新生成按钮 | 按钮 | 可见 | 使用同一照片和风格重新生成 |
| 重新拍照按钮 | 按钮 | 可见 | 回到 CAMERA_READY |
| 查看历史按钮 | 按钮 | 可见 | 导航到 HISTORY |

#### HISTORY

| 元素 | 类型 | 可见性 | 说明 |
|------|------|--------|------|
| HistoryList | 组件 | 可见 | 滚动列表展示历史记录（缩略图 + 风格名 + 时间） |
| 返回按钮 | 按钮 | 可见 | 回到 CAMERA_READY |
| 空状态提示 | 文本 | 条件可见 | 暂无记录时显示 |

### B.3 状态转换图

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌──────────┐   OK手势   ┌──────────┐  倒计时结束  ┌────────────┐
│CAMERA    │──────────▶│COUNTDOWN  │────────────▶│PHOTO_TAKEN │
│READY     │◀──────────┤           │             └─────┬──────┘
└────┬─────┘  张开手掌  └──────────┘                   │
     │                                                     │ 自动
     │                    ┌──────────┐   API成功   ┌───────▼──────┐
     │                    │ANALYZING │◀────────────│ 发送 /analyze │
     │                    └────┬─────┘             └──────────────┘
     │                         │
     │                         │ API返回风格选项
     │                         ▼
     │                  ┌─────────────────┐
     │                  │STYLE_SELECTION   │
     │                  └────┬────────────┘
     │                       │ 用户点击风格卡片
     │                       ▼
     │                  ┌────────────┐  API成功   ┌──────────────┐
     │                  │GENERATING  │◀────────────│ 发送/generate│
     │                  └────┬───────┘             └──────────────┘
     │                       │
     │                       │ 图片返回
     │                       ▼
     │                 ┌─────────────┐
     │    ┌────────────│POSTER_READY  │
     │    │            └──────┬──────┘
     │    │                   │
     │    │   ┌───────────────┤
     │    │   │ 重新拍照       │ 重新生成
     │    │   ▼               ▼
     │    │ ┌────────┐  ┌────────────┐
     │    └─│CAMERA  │  │GENERATING  │
     │      │READY   │  └────────────┘
     │      └───┬────┘
     │          │
     │  ┌───────┴────────┐
     │  │ 点击历史按钮     │
     │  │                 │
     │  │  ┌──────────┐  │
     │  │  │HISTORY   │──┘
     │  │  └──────────┘
     │  │
     │  ▼
     └──┘
```

### B.4 状态转换条件与触发方式

| 当前状态 | 目标状态 | 触发条件 | 触发方式 |
|----------|----------|----------|----------|
| CAMERA_READY | COUNTDOWN | 检测到 OK 手势（持续 ≥ 500ms） | useGestureDetector 回调 |
| COUNTDOWN | CAMERA_READY | 检测到张开手掌 | useGestureDetector 回调 |
| COUNTDOWN | PHOTO_TAKEN | 倒计时 3 → 2 → 1 → 0 完成 | useCountdown 回调 |
| PHOTO_TAKEN | ANALYZING | 照片截取完成 | 自动转换（同步） |
| ANALYZING | STYLE_SELECTION | /api/analyze 返回 3 个风格选项 | API 响应 |
| ANALYZING | ANALYZING | /api/analyze 请求失败 | 自动重试（最多 3 次），超 3 次显示 ErrorDisplay |
| STYLE_SELECTION | GENERATING | 用户点击某个 StyleCard | onClick 事件 |
| GENERATING | POSTER_READY | /api/generate 返回海报图片 | API 响应 |
| GENERATING | GENERATING | /api/generate 请求失败 | 自动重试（最多 2 次），超 2 次显示 ErrorDisplay |
| POSTER_READY | CAMERA_READY | 用户点击"重新拍照" | onClick 事件 |
| POSTER_READY | GENERATING | 用户点击"重新生成" | onClick 事件 |
| POSTER_READY | HISTORY | 用户点击"查看历史" | onClick 事件 |
| HISTORY | CAMERA_READY | 用户点击"返回" | onClick 事件 |
| CAMERA_READY | HISTORY | 用户点击"历史记录"按钮 | onClick 事件 |
| 任意状态（除 POSTER_READY） | CAMERA_READY | 检测到张开手掌 | useGestureDetector 回调（全局安全阀） |

---

## C. 组件设计

### C.1 全局共享类型（`src/types/index.ts`）

```typescript
/** 应用状态枚举 */
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

/** 手势类型 */
export type GestureType = 'ok' | 'open_palm' | 'none';

/** 手势检测事件 */
export interface GestureEvent {
  gesture: GestureType;
  confidence: number;         // 0~1
  detectedAt: number;         // Date.now() 时间戳
}

/** /api/analyze 返回的单个风格选项 */
export interface StyleOption {
  name: string;               // 风格名称，如 "赛博朋克"
  brief: string;              // 一句话描述，如 "霓虹灯光下的未来都市"
  prompt: string;             // 给生图模型的详细提示词
}

/** /api/analyze 响应体 */
export interface AnalyzeResponse {
  options: StyleOption[];
}

/** /api/generate 请求体 */
export interface GenerateRequest {
  photo: string;              // Base64 编码照片（不含 data:image 前缀）
  prompt: string;             // 选中的详细提示词
}

/** /api/generate 响应体 */
export interface GenerateResponse {
  image_url: string;          // 生成的海报图片 URL 或 Base64
  style_name: string;         // 使用的风格名称
}

/** 历史记录条目 */
export interface HistoryItem {
  id: string;
  photo_url: string;          // 原始照片缩略图
  poster_url: string;         // 生成的海报
  style_name: string;
  created_at: string;         // ISO 8601 时间戳
}

/** API 错误 */
export interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
}
```

### C.2 CameraView

```typescript
interface CameraViewProps {
  /** 视频 ref，供外部截帧使用 */
  videoRef: React.RefObject<HTMLVideoElement>;
  /** Canvas ref，供 MediaPipe 绘制骨架使用 */
  canvasRef: React.RefObject<HTMLCanvasElement>;
  /** 是否正在检测手势（倒计时阶段关闭检测可提升性能） */
  detectGesture: boolean;
  /** MediaPipe 手部关键点数据 */
  landmarks: NormalizedLandmark[] | null;
  /** 视频流加载失败回调 */
  onError: (error: Error) => void;
}
```

**职责：**
- 渲染 `<video>` 元素（前置摄像头，`facingMode: 'user'`）
- 渲染同尺寸 `<canvas>` 叠加在视频上方（`position: absolute`）
- 当 `landmarks` 变化时，绘制手部关键点连线（21 个关键点，绿色骨架线 + 红色关键点圆点）
- video 使用 `object-fit: cover`，canvas 保持与 video 完全对齐

### C.3 GestureOverlay

```typescript
interface GestureOverlayProps {
  /** 当前检测到的手势 */
  gesture: GestureType;
  /** 是否已识别到有效手势（用于高亮动效） */
  isGestureDetected: boolean;
  /** 提示文字 */
  hintText: string;
}
```

**职责：**
- 在摄像头画面上方半透明浮层
- 未检测到手势时显示暗色遮罩 + 默认提示文字
- 检测到 OK 手势时显示绿色高亮边框 + "已识别" 文字
- 显示底部手势示意图标（OK 手势图标 / 张开手掌图标）

### C.4 Countdown

```typescript
interface CountdownProps {
  /** 剩余秒数（3, 2, 1） */
  seconds: number;
  /** 倒计时是否已完成 */
  isComplete: boolean;
  /** 倒计时完成回调 */
  onComplete: () => void;
}
```

**职责：**
- 大号数字居中显示，带 CSS 缩放 + 淡入动画
- 数字变化时触发音效（`new Audio('/sounds/countdown-beep.mp3').play()`）
- `isComplete` 时触发 `onComplete` 回调

### C.5 StyleCard

```typescript
interface StyleCardProps {
  /** 风格选项数据 */
  option: StyleOption;
  /** 卡片索引（用于排列动画延迟） */
  index: number;
  /** 用户选中回调 */
  onSelect: (option: StyleOption) => void;
  /** 是否已选中 */
  isSelected: boolean;
}
```

**职责：**
- 展示风格名称（大标题）
- 展示一句话描述（副标题）
- hover 时放大 + 阴影加深
- 点击触发 `onSelect`，选中时边框高亮
- 三张卡片带交错入场动画（`animation-delay: index * 150ms`）

### C.6 StyleSelection

```typescript
interface StyleSelectionProps {
  /** 后端返回的风格选项列表 */
  options: StyleOption[];
  /** 用户选择风格回调 */
  onSelect: (option: StyleOption) => void;
  /** 是否正在加载 */
  isLoading: boolean;
  /** 错误信息 */
  error: string | null;
  /** 重试回调 */
  onRetry: () => void;
}
```

**职责：**
- 容器组件，渲染标题 + 3 个 StyleCard
- 加载中显示 LoadingSpinner
- 错误时显示 ErrorDisplay
- 卡片布局：桌面端三列横排，移动端（暂不 MVP）单列

### C.7 PosterDisplay

```typescript
interface PosterDisplayProps {
  /** 生成的海报图片 URL 或 Base64 */
  posterUrl: string;
  /** 原始照片 Base64（用于对比展示，可选） */
  originalPhotoUrl?: string;
  /** 使用的风格名称 */
  styleName: string;
  /** 下载按钮回调 */
  onDownload: () => void;
  /** 重新生成按钮回调 */
  onRegenerate: () => void;
  /** 重新拍照按钮回调 */
  onRetake: () => void;
  /** 查看历史按钮回调 */
  onViewHistory: () => void;
}
```

**职责：**
- 大图展示生成海报
- 操作按钮栏：保存/下载、重新生成、重新拍照、查看历史
- 下载实现：创建 `<a>` 标签 + `download` 属性 + `URL.createObjectURL(blob)`
- 支持海报图片加载状态（骨架屏或 shimmer）

### C.8 HistoryList

```typescript
interface HistoryListProps {
  /** 历史记录数组 */
  items: HistoryItem[];
  /** 是否正在加载 */
  isLoading: boolean;
  /** 点击某条记录回调（查看大图，可选） */
  onItemClick: (item: HistoryItem) => void;
  /** 返回按钮回调 */
  onBack: () => void;
}
```

**职责：**
- 卡片网格或列表形式展示历史记录
- 每条记录包含：海报缩略图 + 风格名称 + 生成时间
- 空状态显示"暂无历史记录"占位图
- 加载中显示 LoadingSpinner
- 支持下拉加载更多（分页，可选）

### C.9 LoadingSpinner

```typescript
interface LoadingSpinnerProps {
  /** 提示文字 */
  text: string;
  /** 尺寸：sm / md / lg */
  size?: 'sm' | 'md' | 'lg';
}
```

### C.10 ErrorDisplay

```typescript
interface ErrorDisplayProps {
  /** 错误信息 */
  message: string;
  /** 重试按钮回调（不传则不显示重试按钮） */
  onRetry?: () => void;
  /** 重试按钮文字 */
  retryText?: string;
}
```

### C.11 组件间通信方式

```
App.tsx (状态机宿主)
  │
  ├── 持有 AppState、photo (Base64)、styleOptions、selectedOption、posterUrl、historyItems
  │
  ├── useCamera() ───────────────────▶ 管理 videoRef + 媒体流
  ├── useMediaPipeHands(videoRef) ───▶ 产出 landmarks
  ├── useGestureDetector(landmarks) ─▶ 产出 gesture: GestureType
  ├── useCountdown(3, onComplete) ───▶ 产出 seconds, isComplete
  │
  ├── CameraView ◀── videoRef, canvasRef, landmarks
  ├── GestureOverlay ◀── gesture, hintText
  ├── Countdown ◀── seconds, onComplete
  ├── StyleSelection ◀── options, onSelect
  ├── PosterDisplay ◀── posterUrl, onDownload, onRegenerate, ...
  └── HistoryList ◀── items, onBack
```

**通信模式：** 单向数据流（Props Down, Callbacks Up），所有状态集中在 `App.tsx` 管理，子组件通过 Props 接收数据、通过回调函数上报事件。不使用全局状态管理库（Context/Saga 等），MVP 阶段保持简单。

---

## D. MediaPipe Hands 集成

### D.1 初始化流程

```typescript
// src/hooks/useMediaPipeHands.ts

import { Hands, Results, NormalizedLandmark } from '@mediapipe/hands';

interface UseMediaPipeHandsOptions {
  videoRef: React.RefObject<HTMLVideoElement>;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  onResults: (landmarks: NormalizedLandmark[]) => void;
}

// 初始化步骤：
// 1. 创建 Hands 实例
const hands = new Hands({
  locateFile: (file) => {
    return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
  },
});

// 2. 配置参数
hands.setOptions({
  maxNumHands: 1,              // 只检测一只手（MVP 仅需单手 OK 手势）
  modelComplexity: 1,          // 0=Lite, 1=Full（平衡精度与性能）
  minDetectionConfidence: 0.7, // 检测置信度阈值
  minTrackingConfidence: 0.5,  // 追踪置信度阈值
});

// 3. 设置结果回调
hands.onResults((results: Results) => {
  if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
    const landmarks = results.multiHandLandmarks[0]; // 取第一只手
    onResults(landmarks);
    // 同时在 canvas 上绘制骨架
    drawLandmarks(canvasRef.current!, landmarks);
  } else {
    onResults([]); // 未检测到手
  }
});

// 4. 发送帧进行检测（requestAnimationFrame 循环）
const detect = async () => {
  if (videoRef.current && videoRef.current.readyState >= 2) {
    await hands.send({ image: videoRef.current });
  }
  animationFrameId = requestAnimationFrame(detect);
};
```

### D.2 手势检测逻辑

手势判定在 `src/utils/gestureAlgo.ts` 中实现为纯函数，便于单元测试。

```typescript
// src/utils/gestureAlgo.ts

import { NormalizedLandmark } from '@mediapipe/hands';

/** MediaPipe Hands 21 个关键点索引 */
const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_FINGER_MCP = 5;
const INDEX_FINGER_PIP = 6;
const INDEX_FINGER_DIP = 7;
const INDEX_FINGER_TIP = 8;
const MIDDLE_FINGER_TIP = 12;
const RING_FINGER_TIP = 16;
const PINKY_TIP = 20;

export interface GestureResult {
  gesture: 'ok' | 'open_palm' | 'none';
  confidence: number;
}

/**
 * 判定 OK 手势算法：
 * 1. 拇指尖 (4) 与食指尖 (8) 的欧氏距离 < 阈值（两者形成圆圈）
 * 2. 其余三根手指（中指 12、无名指 16、小指 20）的指尖 y 坐标 < 对应 PIP 关节 y 坐标（手指伸展）
 * 3. 手腕 (0) 到中指 MCP (9) 的距离作为归一化因子
 */
function isOkGesture(landmarks: NormalizedLandmark[]): boolean {
  // 拇指尖与食指尖距离
  const thumbTip = landmarks[THUMB_TIP];
  const indexTip = landmarks[INDEX_FINGER_TIP];
  const thumbIndexDist = distance(thumbTip, indexTip);

  // 归一化因子：手腕到食指 MCP 的距离
  const palmSize = distance(landmarks[WRIST], landmarks[INDEX_FINGER_MCP]);
  const normalizedDist = thumbIndexDist / palmSize;

  // 阈值：拇指尖与食指尖距离小于手掌大小的 0.25
  const circleThreshold = 0.25;
  if (normalizedDist > circleThreshold) return false;

  // 中指、无名指、小指伸展：指尖 y < PIP y（屏幕坐标系 y 向下增大）
  const middleExtended = landmarks[MIDDLE_FINGER_TIP].y < landmarks[11].y;
  const ringExtended = landmarks[RING_FINGER_TIP].y < landmarks[14].y;
  const pinkyExtended = landmarks[PINKY_TIP].y < landmarks[18].y;

  return middleExtended && ringExtended && pinkyExtended;
}

/**
 * 判定张开手掌算法：
 * 所有五根手指的指尖 y 坐标 < 对应 PIP 关节 y 坐标
 * （拇指特殊处理：拇指尖 x 与手腕 x 的距离 > 拇指 IP x 与手腕 x 的距离）
 */
function isOpenPalm(landmarks: NormalizedLandmark[]): boolean {
  // 拇指伸展：拇指尖到手腕的水平距离 > 拇指 IP 到手腕的水平距离
  const isRightHand = landmarks[WRIST].x < landmarks[INDEX_FINGER_MCP].x;
  const thumbExtended = isRightHand
    ? landmarks[THUMB_TIP].x < landmarks[3].x   // 右手：拇指尖更靠左
    : landmarks[THUMB_TIP].x > landmarks[3].x;   // 左手：拇指尖更靠右

  // 食指伸展
  const indexExtended = landmarks[INDEX_FINGER_TIP].y < landmarks[INDEX_FINGER_PIP].y;
  // 中指伸展
  const middleExtended = landmarks[MIDDLE_FINGER_TIP].y < landmarks[11].y;
  // 无名指伸展
  const ringExtended = landmarks[RING_FINGER_TIP].y < landmarks[14].y;
  // 小指伸展
  const pinkyExtended = landmarks[PINKY_TIP].y < landmarks[18].y;

  const extendedCount = [thumbExtended, indexExtended, middleExtended, ringExtended, pinkyExtended]
    .filter(Boolean).length;

  // 至少 4 根手指伸展即判定为张开手掌
  return extendedCount >= 4;
}

/** 两点欧氏距离 */
function distance(a: NormalizedLandmark, b: NormalizedLandmark): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + ((a.z || 0) - (b.z || 0)) ** 2);
}

/** 主判定函数 */
export function detectGesture(landmarks: NormalizedLandmark[]): GestureResult {
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

### D.3 手势事件回调机制

```typescript
// src/hooks/useGestureDetector.ts

interface UseGestureDetectorOptions {
  /** 手势检测结果回调 */
  onGestureDetected: (event: GestureEvent) => void;
  /** OK 手势需持续多久才触发（防误触，默认 500ms） */
  okHoldDuration?: number;
  /** 张开手掌需持续多久才触发（默认 300ms） */
  palmHoldDuration?: number;
}

/**
 * 核心逻辑：
 * 1. 接收 landmarks（来自 useMediaPipeHands 的 onResults 回调）
 * 2. 调用 detectGesture(landmarks) 获取当前帧手势
 * 3. 维护一个 "连续检测计数器"：
 *    - 如果当前帧检测到 'ok' 且计数器 < okHoldDuration 对应帧数，则计数器 +1
 *    - 如果当前帧未检测到 'ok'，则计数器归零
 *    - 计数器达到阈值时，触发 onGestureDetected({ gesture: 'ok', ... })
 *    - 触发后重置计数器，防止重复触发
 * 4. 张开手掌同理，但使用独立的计数器
 */
```

**事件流：**

```
MediaPipe 处理帧 → landmarks
  → detectGesture(landmarks) → GestureResult
    → useGestureDetector 内部防抖逻辑
      → onGestureDetected(GestureEvent)
        → App.tsx 根据 gesture 更新 AppState
```

---

## E. API 集成

### E.1 常量定义（`src/constants/index.ts`）

```typescript
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  ANALYZE: '/api/analyze',
  GENERATE: '/api/generate',
  HISTORY: '/api/history',
} as const;

export const TIMEOUTS = {
  ANALYZE_REQUEST: 30_000,    // 30 秒（视觉 LLM 分析可能较慢）
  GENERATE_REQUEST: 60_000,   // 60 秒（图片生成耗时较长）
  HISTORY_REQUEST: 10_000,    // 10 秒
} as const;

export const RETRY_CONFIG = {
  ANALYZE: { maxRetries: 3, delayMs: 2000 },
  GENERATE: { maxRetries: 2, delayMs: 3000 },
} as const;

export const COUNTDOWN_SECONDS = 3;
```

### E.2 /api/analyze 请求/响应处理

**请求：**

```typescript
// src/services/api.ts

export async function analyzePhoto(photoBase64: string): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.ANALYZE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      photo: photoBase64,  // 不含 data:image 前缀的纯 Base64 字符串
    }),
    signal: AbortSignal.timeout(TIMEOUTS.ANALYZE_REQUEST),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  const data: AnalyzeResponse = await response.json();

  // 校验返回数据格式
  if (!data.options || !Array.isArray(data.options) || data.options.length === 0) {
    throw { code: 'INVALID_RESPONSE', message: '后端返回数据格式异常', retryable: true };
  }

  return data;
}
```

**响应示例：**

```json
{
  "options": [
    {
      "name": "赛博朋克",
      "brief": "霓虹灯光下的未来都市战士",
      "prompt": "cyberpunk style portrait, neon lights, futuristic city background, rain, holographic elements, dramatic lighting, cinematic composition, 8K quality..."
    },
    {
      "name": "水墨画",
      "brief": "东方意境的水墨山水风格",
      "prompt": "Chinese ink wash painting style, mountain landscape, mist, flowing water, minimalist brush strokes, traditional Chinese aesthetics, black and white with subtle color accents..."
    },
    {
      "name": "波普艺术",
      "brief": "安迪·沃霍尔式的色彩爆炸",
      "prompt": "pop art style portrait, bold primary colors, halftone dots pattern, comic book aesthetic, high contrast, Andy Warhol inspired, vibrant background..."
    }
  ]
}
```

### E.3 /api/generate 请求/响应处理

**请求：**

```typescript
export async function generatePoster(
  photoBase64: string,
  prompt: string,
): Promise<GenerateResponse> {
  const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.GENERATE}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      photo: photoBase64,
      prompt: prompt,
    } as GenerateRequest),
    signal: AbortSignal.timeout(TIMEOUTS.GENERATE_REQUEST),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  const data: GenerateResponse = await response.json();

  if (!data.image_url) {
    throw { code: 'INVALID_RESPONSE', message: '后端未返回图片', retryable: true };
  }

  return data;
}
```

**响应示例：**

```json
{
  "image_url": "data:image/png;base64,iVBORw0KGgo...",
  "style_name": "赛博朋克"
}
```

或：

```json
{
  "image_url": "http://localhost:8000/static/posters/abc123.png",
  "style_name": "赛博朋克"
}
```

### E.4 GET /api/history 请求处理

```typescript
export async function getHistory(): Promise<HistoryItem[]> {
  const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.HISTORY}`, {
    method: 'GET',
    signal: AbortSignal.timeout(TIMEOUTS.HISTORY_REQUEST),
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return response.json();
}
```

### E.5 错误处理与重试策略

```typescript
// src/services/errorHandler.ts

interface ApiErrorResponse {
  code: string;
  message: string;
  retryable: boolean;
}

/** 解析 HTTP 错误响应 */
async function parseApiError(response: Response): Promise<ApiErrorResponse> {
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

  // 尝试解析后端返回的详细错误信息
  try {
    const body = await response.json();
    if (body.detail) message = body.detail;
    if (body.code) code = body.code;
  } catch {
    // JSON 解析失败，使用默认错误信息
  }

  return { code, message, retryable };
}

/** 带重试的请求包装器 */
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
      // 指数退避：delayMs * 2^attempt
      const delay = config.delayMs * Math.pow(2, attempt);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
```

**错误展示策略：**

| 错误类型 | 用户提示 | 重试行为 |
|----------|----------|----------|
| TIMEOUT | "AI 正在思考，请稍等..." | 自动重试 3 次（analyze）/ 2 次（generate），指数退避 |
| SERVER_ERROR | "服务器开小差了，请稍后重试" | 同上 |
| RATE_LIMITED | "操作太频繁啦，请等几秒再试" | 自动重试，延迟加倍 |
| BAD_REQUEST | "照片质量不佳，请重新拍照" | 不重试，引导用户重新拍照 |
| AUTH_ERROR | "服务异常，请联系管理员" | 不重试 |
| INVALID_RESPONSE | "AI 返回了意外结果，请重试" | 自动重试 |

---

## F. 验收标准

### F.1 验收：项目初始化与构建

- **前置条件：** Node.js 18+ 已安装
- **Playwright 验证步骤：**
  1. 在终端执行 `npm create vite@latest pose-art-generator -- --template react-ts`
  2. `cd pose-art-generator && npm install`
  3. `npm install @mediapipe/hands tailwindcss postcss autoprefixer`
  4. `npm install -D @types/node`
  5. `npx tailwindcss init -p`
  6. 执行 `npm run dev`，终端输出包含 `Local: http://localhost:5173`
  7. 在浏览器中打开 `http://localhost:5173`
  8. 验证页面无空白屏，至少显示 React 默认内容或应用初始界面
  9. 执行 `npm run build`，输出 `dist/` 目录且无 TypeScript 编译错误
- **通过标准：** 项目可正常初始化、开发服务器启动、构建无错误

### F.2 验收：摄像头画面显示

- **前置条件：** 用户设备具备前置摄像头，浏览器已获摄像头权限
- **Playwright 验证步骤：**
  1. 导航到 `http://localhost:5173`
  2. 浏览器弹出摄像头权限请求时，点击"允许"
  3. 等待 `video` 元素出现：`await page.waitForSelector('video', { timeout: 10000 })`
  4. 验证视频流已激活：`const video = page.locator('video'); await expect(video).toHaveAttribute('srcObject')` 或检查 `video.readyState >= 2`
  5. 验证 canvas overlay 叠加在 video 上方：`const canvas = page.locator('canvas.overlay'); await expect(canvas).toBeVisible()`
  6. 验证 video 和 canvas 尺寸一致：`const videoBox = await video.boundingBox(); const canvasBox = await canvas.boundingBox(); expect(Math.abs(videoBox.width - canvasBox.width)).toBeLessThan(5)`
  7. 验证页面显示手势提示文字：`await expect(page.locator('text=OK 手势')).toBeVisible()`
- **通过标准：** 视频流正常显示，canvas overlay 准确叠加，手势提示文字可见

### F.3 验收：MediaPipe 手部骨架绘制

- **前置条件：** 摄像头已启动，MediaPipe 模型已加载
- **Playwright 验证步骤：**
  1. 导航到 `http://localhost:5173`
  2. 允许摄像头权限
  3. 等待 MediaPipe 模型加载完成（检查 console 无 "Failed to load" 错误）
  4. 将手伸入摄像头视野
  5. 等待 2 秒，观察 canvas overlay
  6. 使用 Playwright 截图验证 canvas 上出现非空白内容：
     ```
     const canvas = page.locator('canvas.hand-overlay');
     const canvasData = await canvas.evaluate(el => {
       const ctx = el.getContext('2d');
       return ctx.getImageData(0, 0, el.width, el.height).data;
     });
     // 检查是否存在非透明像素（骨架线条绘制）
     const hasDrawing = canvasData.some((val, i) => i % 4 === 3 && val > 0);
     expect(hasDrawing).toBe(true);
     ```
- **通过标准：** 手部进入视野后，canvas 上实时显示手部骨架线条（绿色连线 + 红色关键点）

### F.4 验收：OK 手势检测与触发拍照

- **前置条件：** 摄像头已启动，手部骨架正常绘制
- **Playwright 验证步骤：**
  1. 导航到 `http://localhost:5173`，允许摄像头权限
  2. 等待页面进入 CAMERA_READY 状态：`await expect(page.locator('[data-state="camera-ready"]')).toBeVisible()`
  3. 模拟 OK 手势（实际测试需真人操作）
  4. 验证页面状态转换为 COUNTDOWN：`await expect(page.locator('[data-state="countdown"]')).toBeVisible()`
  5. 验证倒计时数字显示：
     ```
     await expect(page.locator('.countdown-number')).toHaveText('3');
     await page.waitForTimeout(1100);
     await expect(page.locator('.countdown-number')).toHaveText('2');
     await page.waitForTimeout(1100);
     await expect(page.locator('.countdown-number')).toHaveText('1');
     ```
- **通过标准：** OK 手势触发 3 秒倒计时，数字依次 3 → 2 → 1 显示

### F.5 验收：张开手掌取消倒计时

- **前置条件：** 当前处于 COUNTDOWN 状态
- **Playwright 验证步骤：**
  1. 在 COUNTDOWN 状态下，将手从 OK 手势变为张开手掌
  2. 验证页面立即回到 CAMERA_READY 状态：`await expect(page.locator('[data-state="camera-ready"]')).toBeVisible()`
  3. 验证倒计时数字消失：`await expect(page.locator('.countdown-number')).not.toBeVisible()`
  4. 验证手势提示文字恢复为"请做出 OK 手势"
- **通过标准：** 张开手掌可在倒计时任意时刻取消，立即回到摄像头等待状态

### F.6 验收：照片截取

- **前置条件：** 倒计时结束（1 → 0 过渡）
- **Playwright 验证步骤：**
  1. 倒计时完成后，验证状态转换为 ANALYZING：`await expect(page.locator('[data-state="analyzing"]')).toBeVisible()`
  2. 验证页面显示"正在分析照片..."文字：`await expect(page.locator('text=正在分析')).toBeVisible()`
  3. 验证存在照片缩略图：`await expect(page.locator('img.captured-photo')).toBeVisible()`
  4. 验证照片 Base64 数据长度合理：
     ```
     const src = await page.locator('img.captured-photo').getAttribute('src');
     expect(src.startsWith('data:image/')).toBe(true);
     expect(src.length).toBeGreaterThan(10000); // 合理的照片数据量
     ```
- **通过标准：** 倒计时结束后自动截取当前帧并显示缩略图，进入分析状态

### F.7 验收：/api/analyze 调用与风格选项展示

- **前置条件：** 后端服务已启动（`http://localhost:8000`），/api/analyze 端点可用
- **Playwright 验证步骤：**
  1. 使用 Playwright 拦截网络请求确认 API 被正确调用：
     ```
     const analyzeRequest = page.waitForRequest(req =>
       req.url().includes('/api/analyze') && req.method() === 'POST'
     );
     // 触发拍照流程...
     const request = await analyzeRequest;
     const body = request.postDataJSON();
     expect(body.photo).toBeDefined();
     expect(body.photo.length).toBeGreaterThan(1000);
     ```
  2. Mock /api/analyze 响应返回 3 个风格选项
  3. 验证状态转换为 STYLE_SELECTION：`await expect(page.locator('[data-state="style-selection"]')).toBeVisible()`
  4. 验证显示 3 张风格卡片：`await expect(page.locator('.style-card')).toHaveCount(3)`
  5. 验证每张卡片包含风格名称和描述：
     ```
     const cards = page.locator('.style-card');
     for (let i = 0; i < 3; i++) {
       await expect(cards.nth(i).locator('.style-name')).toBeVisible();
       await expect(cards.nth(i).locator('.style-brief')).toBeVisible();
     }
     ```
- **通过标准：** API 正确发送照片 Base64，接收到 3 个风格选项后展示为 3 张卡片

### F.8 验收：风格选择交互

- **前置条件：** 页面处于 STYLE_SELECTION 状态，3 张风格卡片已展示
- **Playwright 验证步骤：**
  1. hover 第一张风格卡片：`await page.hover('.style-card:first-child')`
  2. 验证 hover 效果（卡片放大/阴影）：
     ```
     const card = page.locator('.style-card:first-child');
     const boxShadow = await card.evaluate(el => getComputedStyle(el).boxShadow);
     expect(boxShadow).not.toBe('none');
     ```
  3. 点击第一张风格卡片：`await card.click()`
  4. 验证卡片被选中（边框高亮）：`await expect(card).toHaveClass(/selected/)`
  5. 验证状态转换为 GENERATING：`await expect(page.locator('[data-state="generating"]')).toBeVisible()`
- **通过标准：** 风格卡片有 hover 交互效果，点击后进入生成状态

### F.9 验收：/api/generate 调用与海报展示

- **前置条件：** 后端 /api/generate 端点可用
- **Playwright 验证步骤：**
  1. 拦截 generate 请求验证参数：
     ```
     const generateRequest = page.waitForRequest(req =>
       req.url().includes('/api/generate') && req.method() === 'POST'
     );
     // 选择风格后...
     const request = await generateRequest;
     const body = request.postDataJSON();
     expect(body.photo).toBeDefined();
     expect(body.prompt).toBeDefined();
     expect(body.prompt.length).toBeGreaterThan(50); // 详细 prompt
     ```
  2. Mock /api/generate 返回海报图片
  3. 验证状态转换为 POSTER_READY：`await expect(page.locator('[data-state="poster-ready"]')).toBeVisible()`
  4. 验证海报图片显示：`await expect(page.locator('img.poster-result')).toBeVisible()`
  5. 验证海报图片加载完成：
     ```
     const posterImg = page.locator('img.poster-result');
     await expect(posterImg).toHaveAttribute('src', /data:image/);
     const naturalWidth = await posterImg.evaluate(el => el.naturalWidth);
     expect(naturalWidth).toBeGreaterThan(0);
     ```
- **通过标准：** API 正确发送照片和 prompt，接收到海报图片后展示在页面上

### F.10 验收：海报操作按钮

- **前置条件：** 页面处于 POSTER_READY 状态
- **Playwright 验证步骤：**
  1. 验证操作按钮可见：
     ```
     await expect(page.locator('button:has-text("保存")')).toBeVisible();
     await expect(page.locator('button:has-text("重新生成")')).toBeVisible();
     await expect(page.locator('button:has-text("重新拍照")')).toBeVisible();
     await expect(page.locator('button:has-text("历史")')).toBeVisible();
     ```
  2. 点击"重新拍照"：
     ```
     await page.locator('button:has-text("重新拍照")').click();
     await expect(page.locator('[data-state="camera-ready"]')).toBeVisible();
     ```
  3. 重新走流程到 POSTER_READY，点击"重新生成"：
     ```
     await page.locator('button:has-text("重新生成")').click();
     await expect(page.locator('[data-state="generating"]')).toBeVisible();
     ```
- **通过标准：** 4 个操作按钮均可点击，"重新拍照"回到摄像头，"重新生成"回到生成状态

### F.11 验收：海报下载

- **前置条件：** 页面处于 POSTER_READY 状态
- **Playwright 验证步骤：**
  1. 监听 download 事件：
     ```
     const downloadPromise = page.waitForEvent('download');
     await page.locator('button:has-text("保存")').click();
     const download = await downloadPromise;
     ```
  2. 验证下载文件：
     ```
     const fileName = download.suggestedFilename();
     expect(fileName).toMatch(/\.(png|jpg|jpeg|webp)$/);
     const path = await download.path();
     const stats = fs.statSync(path);
     expect(stats.size).toBeGreaterThan(10000); // 合理的图片文件大小
     ```
- **通过标准：** 点击保存按钮触发浏览器下载，文件为有效图片格式且大小合理

### F.12 验收：历史记录

- **前置条件：** 后端 /api/history 端点可用，至少存在 1 条历史记录
- **Playwright 验证步骤：**
  1. 在 POSTER_READY 状态点击"历史"按钮：
     ```
     await page.locator('button:has-text("历史")').click();
     await expect(page.locator('[data-state="history"]')).toBeVisible();
     ```
  2. 验证历史记录加载：
     ```
     const historyRequest = page.waitForRequest(req =>
       req.url().includes('/api/history') && req.method() === 'GET'
     );
     const request = await historyRequest;
     expect(request.method()).toBe('GET');
     ```
  3. 验证历史列表显示：
     ```
     await expect(page.locator('.history-item')).toHaveCount(await page.locator('.history-item').count());
     // 至少有 1 条记录
     await expect(page.locator('.history-item').first()).toBeVisible();
     ```
  4. 点击"返回"按钮：
     ```
     await page.locator('button:has-text("返回")').click();
     await expect(page.locator('[data-state="camera-ready"]')).toBeVisible();
     ```
- **通过标准：** 历史记录正确加载和展示，返回按钮功能正常

### F.13 验收：错误处理 — 网络超时

- **前置条件：** 后端未启动或响应超时
- **Playwright 验证步骤：**
  1. 启动前端，确保后端未运行
  2. 使用 mock 手势或按钮触发拍照流程
  3. 等待 analyze 请求超时（30 秒）
  4. 验证 ErrorDisplay 组件显示：
     ```
     await expect(page.locator('.error-display')).toBeVisible();
     await expect(page.locator('.error-message')).toContainText('超时');
     ```
  5. 验证重试按钮存在：`await expect(page.locator('button:has-text("重试")')).toBeVisible()`
  6. 点击重试，验证再次发送请求（通过网络请求计数验证）
- **通过标准：** 超时后显示友好错误信息，重试按钮可正常工作

### F.14 验收：错误处理 — 后端返回错误

- **前置条件：** 后端已启动但 /api/analyze 返回 500
- **Playwright 验证步骤：**
  1. Mock /api/analyze 返回 `{ status: 500, body: { detail: "Vision LLM 服务不可用" } }`
  2. 触发拍照流程
  3. 验证自动重试 3 次（检查请求次数为 3）
  4. 验证最终显示错误信息：
     ```
     await expect(page.locator('.error-message')).toContainText('服务器');
     await expect(page.locator('button:has-text("重试")')).toBeVisible();
     ```
- **通过标准：** 后端错误自动重试 3 次后显示错误信息，用户可手动重试

### F.15 验收：手势全局取消功能

- **前置条件：** 页面处于非 CAMERA_READY 状态（如 ANALYZING 或 STYLE_SELECTION）
- **Playwright 验证步骤：**
  1. 进入 STYLE_SELECTION 状态
  2. 在摄像头前做出张开手掌手势
  3. 验证页面回到 CAMERA_READY：`await expect(page.locator('[data-state="camera-ready"]')).toBeVisible()`
  4. 重复测试：进入 ANALYZING 状态，做出张开手掌
  5. 验证页面回到 CAMERA_READY
- **通过标准：** 张开手掌手势在任意状态下均可触发返回摄像头等待状态（全局安全阀）

### F.16 验收：摄像头权限拒绝

- **前置条件：** 浏览器摄像头权限未授予或被拒绝
- **Playwright 验证步骤：**
  1. 配置 Playwright 浏览器上下文拒绝摄像头权限：
     ```
     const context = await browser.newContext({
       permissions: [],
       // 或在 Chromium 中通过 args 禁用
     });
     ```
  2. 导航到应用
  3. 验证显示权限引导提示：
     ```
     await expect(page.locator('.camera-permission-prompt')).toBeVisible();
     await expect(page.locator('text=摄像头')).toBeVisible();
     ```
- **通过标准：** 无摄像头权限时显示友好的权限引导界面，不出现白屏或 JS 报错

### F.17 验收：UI 响应式基本布局

- **前置条件：** 应用正常运行
- **Playwright 验证步骤：**
  1. 设置视口为 1920x1080（桌面端）：
     ```
     await page.setViewportSize({ width: 1920, height: 1080 });
     ```
  2. 验证摄像头画面占据主区域：`const video = page.locator('video'); const box = await video.boundingBox(); expect(box.width).toBeGreaterThan(800)`
  3. 设置视口为 1280x720：
     ```
     await page.setViewportSize({ width: 1280, height: 720 });
     ```
  4. 验证所有 UI 元素仍可见：`await expect(page.locator('video')).toBeVisible(); await expect(page.locator('.gesture-overlay')).toBeVisible()`
  5. 验证无元素溢出视口（无水平滚动条）：
     ```
     const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
     const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
     expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
     ```
- **通过标准：** 桌面端分辨率下布局正常，无元素溢出或遮挡

### F.18 验收：console 无错误日志

- **前置条件：** 应用正常运行，完整走一遍主流程
- **Playwright 验证步骤：**
  1. 收集所有 console 错误：
     ```
     const errors = [];
     page.on('console', msg => {
       if (msg.type() === 'error') errors.push(msg.text());
     });
     page.on('pageerror', err => errors.push(err.message));
     ```
  2. 完整执行：摄像头启动 → OK 手势 → 倒计时 → 拍照 → 分析 → 选择风格 → 生成 → 查看海报
  3. 验证无未处理的错误：`expect(errors.length).toBe(0)`
  4. 允许排除已知无关错误（如 MediaPipe WASM 警告），但需在测试中明确记录
- **通过标准：** 完整流程走完后 console 无未预期的 error 级别日志

---

## 附录

### A. 状态机实现参考

```typescript
// src/App.tsx 中的状态管理参考
function App() {
  const [appState, setAppState] = useState<AppState>(AppState.CAMERA_READY);
  const [photo, setPhoto] = useState<string>('');
  const [styleOptions, setStyleOptions] = useState<StyleOption[]>([]);
  const [selectedOption, setSelectedOption] = useState<StyleOption | null>(null);
  const [posterUrl, setPosterUrl] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null!);
  const canvasRef = useRef<HTMLCanvasElement>(null!);

  // ... hooks 初始化

  // 手势回调
  const handleGestureDetected = useCallback((event: GestureEvent) => {
    if (event.gesture === 'ok' && appState === AppState.CAMERA_READY) {
      setAppState(AppState.COUNTDOWN);
    } else if (event.gesture === 'open_palm' && appState !== AppState.POSTER_READY) {
      setAppState(AppState.CAMERA_READY);
    }
  }, [appState]);

  // 倒计时完成回调
  const handleCountdownComplete = useCallback(async () => {
    const base64 = captureFrame(videoRef.current!);
    setPhoto(base64);
    setAppState(AppState.ANALYZING);

    try {
      const result = await withRetry(
        () => analyzePhoto(base64),
        RETRY_CONFIG.ANALYZE,
      );
      setStyleOptions(result.options);
      setAppState(AppState.STYLE_SELECTION);
    } catch (err: any) {
      setError(err.message);
    }
  }, []);

  // 风格选择回调
  const handleStyleSelect = useCallback(async (option: StyleOption) => {
    setSelectedOption(option);
    setAppState(AppState.GENERATING);

    try {
      const result = await withRetry(
        () => generatePoster(photo, option.prompt),
        RETRY_CONFIG.GENERATE,
      );
      setPosterUrl(result.image_url);
      setAppState(AppState.POSTER_READY);
    } catch (err: any) {
      setError(err.message);
    }
  }, [photo]);

  // 渲染当前状态对应的 UI
  return (
    <div data-state={appState.toLowerCase()}>
      {appState === AppState.CAMERA_READY && (
        <>
          <CameraView videoRef={videoRef} canvasRef={canvasRef} ... />
          <GestureOverlay gesture={gesture} ... />
        </>
      )}
      {appState === AppState.COUNTDOWN && (
        <>
          <CameraView ... />
          <Countdown seconds={countdownSeconds} onComplete={handleCountdownComplete} />
          <GestureOverlay hintText="张开手掌取消" ... />
        </>
      )}
      {/* ... 其他状态渲染 */}
    </div>
  );
}
```

### B. 关键依赖版本

| 包名 | 版本 | 用途 |
|------|------|------|
| react | ^18.3.0 | UI 框架 |
| react-dom | ^18.3.0 | React DOM 渲染 |
| typescript | ^5.5.0 | 类型系统 |
| vite | ^5.4.0 | 构建工具 |
| @mediapipe/hands | ^0.4.1675469240 | 手部关键点检测 |
| tailwindcss | ^3.4.0 | CSS 工具类框架 |
| @types/react | ^18.3.0 | React 类型定义 |
| @types/react-dom | ^18.3.0 | React DOM 类型定义 |

### C. 环境变量

```bash
# .env.local（前端）
VITE_API_BASE_URL=http://localhost:8000
```
