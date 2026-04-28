# SlangToon - AI Slang Comic Generator

> SOLID / KISS / DRY / YAGNI

## Project Overview

**SlangToon** is an AI-powered slang comic generator + **art gallery** for exhibition: user makes OK gesture via camera -> GLM-4.6V generates random slang (auto-deduplicated) + 3-6 panel comic script -> user previews script -> confirmed -> Qwen Image 2.0 generates comic strip -> display/download. **Idle 20s auto-enters art gallery mode**, Wave gesture to wake.

### Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript 5.7 (strict), Vite 6, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12, LangGraph |
| Gesture | MediaPipe Hands (OK / Open Palm / Wave) |
| Text LLM | GLM-4.6V (Zhipu BigModel, OpenAI-compatible) |
| Image Gen | Qwen Image 2.0 (DashScope) / Gemini 3.1 Flash (OpenRouter) / GPT-Image-2 (Replicate) — provider switchable |
| Package | `uv` (Python), `npm` (Frontend) |
| Config | `pydantic-settings` + `.env` |
| Tracing | LangSmith (optional, 7-day retention) |

### Core Workflow

```
Camera -> OK gesture -> GLM-4.6V generates slang + script (deduplicated) -> User preview -> Confirmed -> Qwen/Gemini/GPT-Image-2 generates image
     -> Display comic -> [20s idle] -> Art Gallery (history carousel) -> [Wave] -> Back to camera
```

### Frontend State Machine (7 states)

```
                    +-- 20s idle --> GALLERY
                    |                   ^    |
                    |         [Wave]    |    | 8s auto-rotate
                    |                   v    |
  CAMERA_READY ---[OK]---> SCRIPT_LOADING ---> SCRIPT_PREVIEW
       ^                  |fail                 |               | [Generate]
       |                  v                     v               v
       |            CAMERA_READY        COMIC_GENERATING    COMIC_READY
       |                                                        |
       +------------------------ COMIC_READY <-----------------+
                          |
                     [New Slang / open_palm]
                          |
                          v
                   CAMERA_READY / HISTORY
```

**Gesture Mapping:**

| Gesture | Current State | Target State |
|---------|---------------|--------------|
| OK | CAMERA_READY | SCRIPT_LOADING |
| Wave | GALLERY | CAMERA_READY |
| Open Palm | any (non-generating) | CAMERA_READY |

**Idle Rule**: `CAMERA_READY` / `COMIC_READY` idle 20s -> `GALLERY`

### Requirements

- Python 3.12+, Node.js 18+, [uv](https://docs.astral.sh/uv/)
- API Keys: Zhipu BigModel (GLM-4.6V) + DashScope (Qwen Image 2.0) or OpenRouter (Gemini 3.1 Flash) or Replicate (GPT-Image-2)

---

## Project Structure

```
SlangToon/
├── backend/                      # FastAPI backend
│   ├── run.py                    # Backend entry (uvicorn, port 8889)
│   └── app/
│       ├── main.py               # App factory + lifespan + CORS + static mount
│       ├── config.py             # Pydantic Settings (from ../.env)
│       ├── dependencies.py       # FastAPI DI
│       ├── logging_config.py     # Logging (file + console + request_id)
│       ├── middleware.py         # RequestIdMiddleware
│       ├── slang_blacklist.py    # Slang dedup blacklist (JSON, max 50)
│       ├── routers/
│       │   ├── script.py         # POST /api/generate-script
│       │   ├── comic.py          # POST /api/generate-comic
│       │   ├── history.py        # GET  /api/history
│       │   └── traces.py         # GET  /api/traces
│       ├── schemas/
│       │   ├── common.py         # ApiResponse envelope + ErrorCode
│       │   ├── script.py         # ScriptData / Panel (panel_count: 3-6)
│       │   ├── comic.py          # ComicRequest / ComicResponse
│       │   └── history.py        # HistoryItem / HistoryResponse
│       ├── services/
│       │   ├── llm_client.py           # GLM-4.6V (OpenAI-compatible, retry + backoff)
│       │   ├── image_gen_client.py     # Backward-compatible wrapper -> provider
│       │   ├── image_gen/              # Provider abstraction layer
│       │   │   ├── base.py             # BaseImageGenProvider (abstract)
│       │   │   ├── dashscope_provider.py   # Qwen Image 2.0
│       │   │   ├── openrouter_provider.py  # Gemini 3.1 Flash
│       │   │   ├── replicate_provider.py   # GPT-Image-2 (via Replicate)
│       │   │   └── factory.py          # create_image_gen_client()
│       │   ├── history_service.py      # History CRUD (JSON file)
│       │   └── comic_service.py        # (legacy, now handled by graph)
│       ├── graphs/                     # LangGraph workflows
│       │   ├── state.py                # WorkflowState (TypedDict)
│       │   ├── script_graph.py         # START -> script_node -> END
│       │   ├── comic_graph.py          # START -> prompt -> [condense] -> comic -> save -> END
│       │   ├── trace_models.py         # Trace data models
│       │   ├── trace_store.py          # Trace file storage + retention
│       │   └── trace_collector.py      # Trace invocation wrapper
│       ├── nodes/                      # LangGraph nodes
│       │   ├── script_node.py          # Generate slang + script (blacklist integrated)
│       │   ├── prompt_node.py          # Build visual prompt from panels
│       │   ├── condense_node.py        # Truncate prompt if > 950 tokens
│       │   ├── comic_node.py           # Image gen (2688x1536, 16:9)
│       │   └── save_node.py            # Save image + history record
│       └── prompts/
│           ├── script_prompt.py        # Slang + script system prompt (blacklist)
│           ├── comic_prompt.py         # Visual composition prompt + token counting
│           └── condense_prompt.py      # Prompt condensation
├── frontend/                     # React 19 + TypeScript + Vite
│   ├── vite.config.ts            # Vite config + API proxy -> localhost:8889
│   ├── tsconfig.app.json         # strict: true
│   └── src/
│       ├── main.tsx
│       ├── App.tsx               # Root: 7-state machine + idle timer + gallery
│       ├── components/
│       │   ├── CameraView/           # Camera feed + gesture overlay
│       │   ├── ScriptPreview/        # Slang + panel preview
│       │   ├── ComicDisplay/         # Fullscreen immersive comic + auto-fading labels
│       │   ├── GalleryView/          # Fullscreen museum-style crossfade carousel
│       │   ├── HistoryList/          # History list
│       │   ├── GlowBackground/      # Animated glow background
│       │   ├── GestureProgressRing/  # Gesture hold progress indicator
│       │   ├── GestureHint/          # Gesture instruction overlay
│       │   ├── GlassButton.tsx       # Glass-morphism button
│       │   ├── PageTransition.tsx    # Page transition animation
│       │   ├── LoadingOrb.tsx        # Loading animation
│       │   └── ErrorDisplay.tsx      # Error display
│       ├── hooks/
│       │   ├── useCamera.ts              # Camera stream management
│       │   ├── useMediaPipeHands.ts      # MediaPipe Hands init
│       │   ├── useGestureDetector.ts     # Frame-level gesture recognition
│       │   └── useGestureConfirm.ts      # Gesture hold/confirmation logic
│       ├── services/
│       │   └── api.ts                # Fetch wrapper + endpoint functions
│       ├── types/
│       │   └── index.ts              # AppState (7), GestureType (ok|open_palm|wave|none)
│       ├── constants/
│       │   └── index.ts              # API_BASE_URL / ENDPOINTS / TIMEOUTS
│       └── utils/
│           └── gestureAlgo.ts        # detectGesture + WaveBuffer + detectWave
├── tests/
│   ├── backend/
│   │   ├── conftest.py               # Shared fixtures
│   │   ├── unit/                     # 29 test files (all services/nodes/graphs/routes)
│   │   └── integration/              # Real API + LangSmith + trace tests
│   ├── frontend/
│   │   ├── unit/                     # Vitest (smoke.test.ts)
│   │   └── e2e/                      # Playwright (core-flow.spec.ts)
│   └── e2e/                          # Full-stack E2E (e2e_test.py)
├── pyproject.toml                # Python deps (FastAPI, LangGraph, LangSmith, etc.)
├── start.py                      # Unified launcher (backend:8889 + frontend:5174)
└── .env.example                  # API keys + provider config template
```

### Backend Module Dependencies

```
routers/  -->  services/  -->  (llm_client | image_gen/ | prompts/ | slang_blacklist | storage/)  -->  schemas/ + config
              graphs/    -->  nodes/  -->  (services | prompts | slang_blacklist)
```

**Two LangGraph Pipelines:**
1. **ScriptGraph**: `START -> script_node -> END` — generates slang + 3-6 panel script
2. **ComicGraph**: `START -> prompt_node -> [condense_node if >950 tokens] -> comic_node -> save_node -> END` — builds visual prompt, generates 16:9 image, saves

---

## API Spec

### Envelope

```json
{ "code": 0, "message": "success", "data": { ... } }
```

### Endpoints

| Endpoint | Method | Request | Response data |
|----------|--------|---------|---------------|
| `/api/generate-script` | POST | `{}` | `{ slang, origin, explanation, panel_count, panels: Panel[] }` |
| `/api/generate-comic` | POST | `{ slang, origin, explanation, panel_count, panels }` | `{ comic_url, thumbnail_url, history_id }` |
| `/api/history` | GET | `?page&page_size` | `{ items, total, page, page_size, total_pages }` |
| `/api/traces` | GET | `?days&limit` | Trace records |
| `/health` | GET | - | `{ status, app }` |

### Conventions

- **Field naming**: `snake_case` everywhere (`panel_count`, `comic_url`, `page_size`)
- **panel_count**: 3-6 (for 2x2/2x3 grid layouts)
- **Vite proxy**: `/api` and `/data` -> `http://localhost:8889`
- **Comic storage**: `data/comics/YYYY-MM-DD/{uuid}.png`
- **Blacklist storage**: `data/slang_blacklist.json` (max 50)
- **Image size**: 2688x1536 (16:9 landscape)

### Error Codes

```python
class ErrorCode:
    BAD_REQUEST = 40001
    SCRIPT_LLM_FAILED = 50001
    SCRIPT_LLM_INVALID = 50002
    COMIC_LLM_FAILED = 50003
    COMIC_LLM_INVALID = 50004
    IMAGE_GEN_FAILED = 50005
    IMAGE_DOWNLOAD_FAILED = 50006
    INTERNAL_ERROR = 50007
```

---

## Testing

### Structure

```
tests/backend/unit/       # 29 files — all modules covered
tests/backend/integration/ # Real API, LangSmith, trace v2
tests/frontend/unit/      # Vitest smoke tests
tests/frontend/e2e/       # Playwright core-flow
tests/e2e/                # Full-stack E2E
```

### Shared Fixtures (conftest.py)

- `tmp_data_dir` — temp data dir + env vars
- `client` — httpx AsyncClient (ASGI)
- `mock_script_data` — mock LLM script response
- `mock_comic_prompt` — mock visual prompt
- `mock_image_gen_b64` — mock 64x64 PNG

### Naming Convention

```python
def test_<method>_<scenario>_<expected>(): ...
```

---

## Code Standards

### Python Backend

- FastAPI + Pydantic v2, `httpx` async with retry + backoff
- `pydantic-settings` from `../.env`, `logging.getLogger(__name__)`
- Custom exceptions per client: `LLMTimeoutError`, `LLMApiError`, `ImageGenApiError`, `ImageGenTimeoutError`
- Image gen provider abstraction: `BaseImageGenProvider` -> DashScope / OpenRouter / Replicate (factory pattern)
- Type annotations: Python 3.12 style

### TypeScript Frontend

- React 19 function components + Hooks, Vite 6, Tailwind CSS 4
- `tsconfig.app.json` strict: true
- Component structure: one directory per component (`.tsx` + `.test.tsx`)
- App-level state machine (7 states), no global state library
- Gesture confirmation via `useGestureConfirm` hook (hold-to-activate pattern)

### Principles

- **S**: Routers = HTTP only, business logic in services/nodes, data in schemas
- **O**: Extend via Pydantic models, image gen via provider abstraction (DashScope / OpenRouter / Replicate)
- **D**: Settings injected, image gen via factory
- **KISS**: No over-abstraction for current scale
- **DRY**: Shared fixtures in conftest, shared types in `types/index.ts`
- **YAGNI**: Only implement what's needed now

---

## Quick Commands

```bash
# Start all (backend + frontend)
python start.py

# Backend only (port 8889)
uv run python backend/run.py

# Frontend only (port 5174)
cd frontend && npm run dev

# Backend unit tests
uv run pytest tests/backend/unit/ -v

# Backend integration tests (needs API keys)
uv run pytest tests/backend/integration/test_real_api.py -v -s

# Frontend unit tests
cd frontend && npx vitest run

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend build
cd frontend && npm run build

# Frontend E2E
cd frontend && npx playwright test

# Full-stack E2E
uv run python tests/e2e/e2e_test.py
```

---

## Pre-commit Checklist

- [ ] `uv run pytest tests/backend/unit/ -v` passes
- [ ] `cd frontend && npx vitest run` passes
- [ ] `cd frontend && npx tsc --noEmit` zero errors
- [ ] New/modified backend code has tests
- [ ] API fields use `snake_case`
- [ ] Frontend/backend types in sync
- [ ] SOLID / KISS / DRY / YAGNI
- [ ] No duplicate code
- [ ] Dependency direction: `routers -> services/nodes -> clients/prompts/storage -> schemas/config`
