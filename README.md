# MagicPose

**AI 驱动的姿态创意海报生成器**

对着镜头摆个造型，AI 自动识别你的姿态，挑选艺术风格，几秒内生成专属创意海报。

## 工作流程

```
摄像头  -->  手势检测  -->  姿态分析（视觉 LLM）  -->  风格选择  -->  海报生成（AI）
  ^                                                                                            |
  |                                                                                            v
MediaPipe Hands                                                              下载 / 分享海报
```

1. **摆造型** - 站在摄像头前，比出手势触发拍照
2. **AI 分析** - GLM-4.6V 视觉模型分析你的姿态，推荐匹配的艺术风格
3. **生成海报** - 选择喜欢的风格，Qwen Image 2.0 为你生成创意海报

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18, TypeScript, Vite, Tailwind CSS |
| 后端 | FastAPI, Python 3.12 |
| 手势检测 | MediaPipe Hands |
| 视觉大模型 | GLM-4.6V（智谱 BigModel） |
| 图像生成 | Qwen Image 2.0（通义 DashScope） |
| 包管理 | uv（Python）、npm（前端） |

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) 包管理器
- API 密钥：[智谱 BigModel](https://open.bigmodel.cn/)（GLM-4.6V）+ [通义 DashScope](https://dashscope.aliyuncs.com/)（Qwen Image 2.0）

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/pheonix2006/MagicPose.git
cd MagicPose

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API 密钥

# 3. 安装后端依赖
uv sync

# 4. 安装前端依赖
cd frontend && npm install && cd ..

# 5. 启动项目
python start.py
```

启动后前端访问 `http://localhost:5173`，后端 API 运行在 `http://localhost:8888`。

### 一键启动

```bash
python start.py
```

该脚本会自动检查依赖、启动后端服务，并启动前端开发服务器。

## 项目结构

```
MagicPose/
├── backend/            # FastAPI 后端
│   └── app/
│       ├── routers/    # API 路由（analyze、generate、history）
│       ├── services/   # LLM 客户端、图像生成客户端
│       ├── storage/    # 基于文件的海报存储
│       └── config.py   # Pydantic 配置
├── frontend/           # React + TypeScript
│   └── src/
│       ├── components/ # CameraView、PosterDisplay、StyleSelection 等
│       ├── hooks/      # useCamera、useGestureDetector、useMediaPipeHands
│       ├── services/   # API 客户端
│       └── utils/      # captureFrame 帧捕获
├── tests/              # 统一测试目录
│   ├── backend/        # 单元测试 + 集成测试
│   ├── frontend/       # 单元测试 + E2E 测试
│   └── e2e/            # 全栈端到端测试
├── docs/               # 设计文档与计划
├── .env.example        # 环境变量模板
├── pyproject.toml      # Python 项目配置（uv）
└── start.py            # 统一启动脚本
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/analyze` | POST | 分析姿态照片，推荐艺术风格 |
| `/api/generate` | POST | 根据姿态 + 风格生成海报 |
| `/api/history` | GET | 获取生成历史记录 |

## 测试

```bash
# 后端单元测试
uv run pytest tests/backend/unit/ -v

# 前端单元测试
cd frontend && npx vitest run

# 前端 E2E 测试
cd frontend && npx playwright test

# 全栈 E2E 测试（需要运行中的后端服务）
uv run python tests/e2e/e2e_test.py
```

## License

MIT
