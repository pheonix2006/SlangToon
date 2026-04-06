# SlangToon - AI Slang-to-Comic Generator

AI-powered slang-to-comic generator with **art gallery mode**. Trigger via OK hand gesture, watch GLM-4.6V produce a random English slang with a multi-panel comic script, then Qwen Image 2.0 renders it into a comic strip. Idle for 20s and it becomes an art gallery — wave to wake.

## Workflow

```
Camera -> OK Gesture -> GLM-4.6V (slang + 8-12 panel script) -> User Preview
     -> Qwen Image 2.0 (comic strip) -> [20s idle] -> Art Gallery (auto-carousel)
                                                              ^-- [Wave] --+
```

1. **Trigger** — Show an OK hand gesture to the camera
2. **Generate Script** — GLM-4.6V picks a random slang (**deduplicated**) and writes a multi-panel comic script
3. **Preview** — Review the slang, origin, explanation, and panel descriptions
4. **Generate Comic** — Confirm to generate a comic strip image via Qwen Image 2.0
5. **Gallery Mode** — After 20s of inactivity, auto-enter art gallery mode showing history works in a museum-style carousel
6. **Wake Up** — Wave your hand to exit gallery and return to camera mode

### State Machine (7 States)

```
CAMERA_READY ──[OK]──→ SCRIPT_LOADING ──→ SCRIPT_PREVIEW ──[Generate]──→ COMIC_GENERATING → COMIC_READY
   ↑    │                                                                              │
   │    │  [open_palm]                                              [New Slang / open_palm]
   │    ←──────────────────────────────────────────────────────────────┘
   │
   │         ┌─ 20s idle ──→ GALLERY (art carousel)
   │         │                    ↑
   │         │              [Wave]
   │         └────────────────────┘
   │
   └──[History button]──→ HISTORY
```

| State | Trigger | Description |
|-------|---------|-------------|
| `CAMERA_READY` | Default / goHome / Wave from GALLERY | Camera active, waiting for gesture |
| `SCRIPT_LOADING` | OK gesture | LLM generating script |
| `SCRIPT_PREVIEW` | Script ready | User reviews slang + panels |
| `COMIC_GENERATING` | User confirms | Qwen generating image |
| `COMIC_READY` | Comic ready | Display result, can create new or idle |
| `GALLERY` | 20s idle | Auto art gallery carousel |
| `HISTORY` | History button | Browse past creations |

### Gesture Map

| Gesture | Source State | Target State |
|--------|------------|-------------|
| OK sign | CAMERA_READY | SCRIPT_LOADING |
| Open palm | Any (except COMIC_READY) | CAMERA_READY |
| **Wave** | **GALLERY** | **CAMERA_READY** |

## Features

### Slang Deduplication
- Independent blacklist (`data/slang_blacklist.json`) tracks up to 50 recently used slangs
- Dynamically injected into LLM system prompt: "ALREADY USED SLANGS — DO NOT PICK THESE"
- Only written on successful generation; failures never pollute the blacklist

### Art Gallery Mode
- Left-right split layout: museum label (slang/origin/explanation) + comic image
- 8-second auto-advance with 1200ms opacity fade transition
- Dot indicators, entrance black-fade animation
- Empty state: brand screensaver with breathing glow effect
- Camera stays alive (hidden) for continuous wave detection

### Wave Gesture Detection
- Ring buffer captures wrist x-coordinates across ~15 frames (~0.5s)
- Peak-to-peak amplitude detection (threshold: 0.12)
- Cooldown mechanism prevents rapid re-triggering
- Non-none gestures (OK/palm) clear the wave buffer to avoid false positives

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript 5.7 (strict), Vite 6, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12, LangGraph |
| Gesture | MediaPipe Hands (OK, Open Palm, **Wave**) |
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
| `/api/generate-script` | POST | Generate random slang + 8-12 panel comic script (deduped) |
| `/api/generate-comic` | POST | Generate comic image from a confirmed script |
| `/api/history` | GET | Paginated generation history |
| `/api/traces` | GET | LangSmith request traces |
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
│       ├── main.py           # App factory + lifespan + middleware
│       ├── config.py         # Pydantic Settings (.env)
│       ├── dependencies.py   # FastAPI dependency injection
│       ├── graphs/           # LangGraph workflow definitions
│       ├── nodes/            # LangGraph nodes (script_node with blacklist)
│       ├── routers/          # API routes (script, comic, history, traces)
│       ├── services/         # Business logic (LLM, image gen, history)
│       ├── schemas/          # Pydantic request/response models
│       ├── storage/          # File-based comic image storage
│       ├── prompts/          # LLM prompt templates (+ dynamic blacklist injection)
│       └── slang_blacklist.py # Slang dedup manager (JSON persistence)
├── frontend/                 # React 19 + TypeScript + Vite
│   └── src/
│       ├── components/
│       │   ├── CameraView/       # Camera feed overlay
│       │   ├── ScriptPreview/    # Slang + panels review
│       │   ├── ComicDisplay/     # Final comic result
│       │   ├── HistoryList/      # Past creations browser
│       │   ├── GalleryView/      # Art gallery carousel (NEW)
│       │   ├── ErrorDisplay.tsx  # Error message component
│       │   └── LoadingOrb.tsx    # Loading animation
│       ├── hooks/
│       │   ├── useCamera.ts          # Webcam management
│       │   ├── useGestureDetector.ts # OK / Palm / Wave detection
│       │   └── useMediaPipeHands.ts  # MediaPipe initialization
│       ├── services/         # API client (fetch wrapper)
│       ├── types/
│       │   ├── index.ts          # AppState (7 states) + GestureType (+wave)
│       │   └── __tests__/        # Type unit tests
│       └── utils/
│           └── gestureAlgo.ts   # detectGesture + WaveBuffer + detectWave
├── tests/
│   ├── backend/unit/          # pytest unit tests (194 tests)
│   │   ├── test_config.py
│   │   ├── test_slang_blacklist.py  # Blacklist module tests
│   │   ├── test_prompts.py          # Prompt template tests
│   │   ├── test_script_node.py      # Node integration tests
│   │   └── ...                       # Other service/route/schema tests
│   ├── frontend/             # Vitest unit + Playwright E2E (78 tests)
│   └── e2e/                   # Full-stack E2E
├── docs/                     # Design documents (plans + specs)
├── .env.example
├── pyproject.toml
└── start.py                  # One-click launcher (both frontend & backend)
```

## Testing

```bash
# Backend unit tests (194 tests)
uv run pytest tests/backend/unit/ -v

# Frontend unit tests (78 tests)
cd frontend && npx vitest run

# TypeScript type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build

# Frontend E2E tests
cd frontend && npx playwright test

# Full-stack E2E tests
uv run python tests/e2e/e2e_test.py
```

## License

MIT
