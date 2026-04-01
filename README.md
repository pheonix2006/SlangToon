# SlangToon - AI Slang-to-Comic Generator

AI-powered slang-to-comic generator. Trigger via OK hand gesture in front of the camera, and watch GLM-4.6V produce a random English slang with a multi-panel comic script, then Qwen Image 2.0 renders it into a single 16:9 comic strip.

## Workflow

```
Camera -> OK Gesture -> GLM-4.6V (slang + 4-6 panel script) -> User Preview -> Qwen Image 2.0 (comic strip)
```

1. **Trigger** - Show an OK hand gesture to the camera
2. **Generate Script** - GLM-4.6V picks a random slang and writes a multi-panel comic script
3. **Preview** - Review the slang, origin, explanation, and panel descriptions
4. **Generate Comic** - Confirm to generate a comic strip image via Qwen Image 2.0
5. **Download** - View and download the result

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript 5.7, Vite 6, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12 |
| Gesture | MediaPipe Hands |
| LLM | GLM-4.6V ([BigModel](https://open.bigmodel.cn/)) |
| Image Gen | Qwen Image 2.0 ([DashScope](https://dashscope.aliyuncs.com/)) |
| Package | [uv](https://docs.astral.sh/uv/) (Python), npm (frontend) |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) package manager
- API keys: [BigModel](https://open.bigmodel.cn/) (GLM-4.6V) + [DashScope](https://dashscope.aliyuncs.com/) (Qwen Image 2.0)

### Install & Run

```bash
# 1. Clone and enter the project
git clone <repo-url> && cd SlangToon

# 2. Configure environment variables
cp .env.example .env
# Edit .env and fill in your API keys

# 3. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 4. Start
python start.py
```

Frontend: `http://localhost:5173` | Backend API: `http://localhost:8888`

You can also run them separately:

```bash
# Backend only
uv run python backend/run.py

# Frontend only
cd frontend && npm run dev
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generate-script` | POST | Generate random slang + 4-6 panel comic script |
| `/api/generate-comic` | POST | Generate comic image from a confirmed script |
| `/api/history` | GET | Paginated generation history |
| `/health` | GET | Health check |

All endpoints return a unified `ApiResponse` envelope:

```json
{ "code": 0, "message": "success", "data": { ... } }
```

## Project Structure

```
SlangToon/
├── backend/                  # FastAPI backend
│   ├── run.py                # Uvicorn entry point
│   └── app/
│       ├── main.py           # App factory + lifespan
│       ├── config.py         # Pydantic Settings (.env)
│       ├── routers/          # API routes (script, comic, history)
│       ├── services/         # Business logic (LLM, image gen, history)
│       ├── schemas/          # Pydantic request/response models
│       ├── storage/          # File-based comic image storage
│       └── prompts/          # LLM prompt templates
├── frontend/                 # React 19 + TypeScript + Vite
│   └── src/
│       ├── components/       # CameraView, ScriptPreview, ComicDisplay, etc.
│       ├── hooks/            # useCamera, useGestureDetector, useMediaPipeHands
│       ├── services/         # API client
│       ├── types/            # TypeScript types and AppState enum
│       └── utils/            # Gesture recognition algorithm
├── tests/
│   ├── backend/              # Unit + integration tests
│   ├── frontend/             # Vitest unit + Playwright E2E
│   └── e2e/                  # Full-stack E2E
├── docs/                     # Design documents
├── .env.example
├── pyproject.toml
└── start.py                  # One-click launcher (both frontend & backend)
```

## Testing

```bash
# Backend unit tests
uv run pytest tests/backend/unit/ -v

# Frontend unit tests
cd frontend && npx vitest run

# Frontend E2E tests
cd frontend && npx playwright test

# Full-stack E2E tests
uv run python tests/e2e/e2e_test.py
```

## License

MIT
