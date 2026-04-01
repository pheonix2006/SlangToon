# SlangToon — Slang-to-Comic Generator Design

> Date: 2026-04-01
> Status: Approved (Revised)

## Overview

**SlangToon** transforms the existing MagicPose project into an AI-powered slang-to-comic generator. The user triggers via OK hand gesture, the system generates a random Eastern/Western slang with a modern reinterpretation as a multi-panel comic script, then produces a single 16:9 comic strip image via Qwen Image 2.0.

### Core Flow

```
Camera (gesture detection only, no photo)
  → OK gesture detected
  → Single LLM call: random slang + 4-6 panel comic script (English)
  → User previews slang + script, can Shuffle or Generate
  → Single Qwen Image 2.0 call: one 16:9 comic strip image
  → Display comic → Download / New
```

### Target Users

Foreign users. All story content, dialogue, and comic text in English. Slang origin can be Eastern or Western.

---

## Frontend State Machine

5 states, linear flow with two loop-back points:

```
CAMERA_READY → SCRIPT_LOADING → SCRIPT_PREVIEW → COMIC_GENERATING → COMIC_READY
                    ↑                  |                   |
                    |── Shuffle ────────┘                   |
                    |                                        |
                    └──────── New ───────────────────────────┘
```

### State Definitions

| State | What user sees | Trigger / Action |
|-------|---------------|------------------|
| `CAMERA_READY` | Full-screen camera with hand landmark overlay. "Make an OK sign" hint text. | OK gesture → `SCRIPT_LOADING` |
| `SCRIPT_LOADING` | Loading spinner + "Creating something fun..." | Auto: `POST /api/generate-script` → `SCRIPT_PREVIEW` |
| `SCRIPT_PREVIEW` | Slang title + origin + explanation + panel-by-panel descriptions. "Shuffle" and "Generate Comic" buttons. | Shuffle → `SCRIPT_LOADING` · Generate → `COMIC_GENERATING` |
| `COMIC_GENERATING` | Loading spinner + "Drawing your comic..." | Auto: `POST /api/generate-comic` → `COMIC_READY` |
| `COMIC_READY` | Full 16:9 comic image. Download, Share, New Slang buttons. | New → `CAMERA_READY` |

### Layout

Full-screen step flow. Each state occupies the full viewport. No split views. Camera only visible in `CAMERA_READY` state (not needed elsewhere since no photo is taken).

### Error Recovery

- `SCRIPT_LOADING` fails → back to `CAMERA_READY` (show error, tap to retry)
- `COMIC_GENERATING` fails → back to `SCRIPT_PREVIEW` (preserve script data, user can retry)

---

## API Design

### `POST /api/generate-script`

Generate a random slang with comic script.

**Request**:
```json
{}
```

Uses `ScriptRequest(BaseModel)` with no fields (reserved for future parameters like language preference). `model_config = ConfigDict(extra="forbid")`.

**Response**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "slang": "Break a leg",
    "origin": "Western theater tradition",
    "explanation": "Used to wish good luck before a performance",
    "panel_count": 4,
    "panels": [
      {
        "scene": "A nervous actor paces backstage, clutching a crumpled script...",
        "dialogue": "Narrator: \"It was opening night...\""
      },
      {
        "scene": "Friends gather around, giving thumbs up with big smiles.",
        "dialogue": "Friend: \"You've got this!\""
      }
    ]
  }
}
```

**Constraints**:
- `panel_count`: 4-6 (LLM decides)
- `panels`: exactly `panel_count` entries
- All text in English
- Slang can be Eastern or Western origin

### `POST /api/generate-comic`

Generate a single comic strip image from the script.

**Request**:
```json
{
  "slang": "Break a leg",
  "origin": "Western theater tradition",
  "explanation": "Used to wish good luck before a performance",
  "panel_count": 4,
  "panels": [
    { "scene": "...", "dialogue": "..." }
  ]
}
```

Includes `origin` and `explanation` for full cultural context when building the image prompt.

**Response**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "comic_url": "/data/2026-04-01/abc123.png",
    "thumbnail_url": "/data/2026-04-01/abc123_thumb.png",
    "history_id": "abc123"
  }
}
```

**Image spec**: 16:9 aspect ratio, size `2688*1536` (Qwen Image 2.0 recommended 16:9 resolution), single image with multi-panel comic layout (borders, speech bubbles, panel dividers). `prompt_extend` parameter set to `false` to preserve exact prompt control.

### `GET /api/history`

Paginated history of generated comics.

**HistoryItem schema**:
```python
class HistoryItem(BaseModel):
    id: str
    slang: str
    origin: str
    explanation: str
    panel_count: int
    comic_url: str
    thumbnail_url: str
    comic_prompt: str          # The visual prompt sent to Qwen
    created_at: str
```

Same pagination structure as existing: `{ items, total, page, page_size, total_pages }`.

### `GET /health` (unchanged)

---

## Backend Architecture

### New Service Layer

```
routers/
  script.py          → script_service.py → llm_client.py (text-only call)
  comic.py           → comic_service.py  → image_gen_client.py (text-to-image)
  history.py         → history_service.py (adapted fields)

services/
  script_service.py  # Single LLM call: slang + panels (text-only, no image)
  comic_service.py   # Build image prompt from script → Qwen Image 2.0 (text-to-image)
  llm_client.py      # MODIFY: add chat() method for text-only calls
  image_gen_client.py # MODIFY: add generate_from_text() for text-to-image
  history_service.py # REUSED (field adaptation)

prompts/
  script_prompt.py   # New: instruct LLM to generate slang + comic script JSON
  comic_prompt.py    # New: build visual prompt for multi-panel 16:9 comic

schemas/
  script.py          # ScriptRequest, ScriptResponse, Panel
  comic.py           # ComicRequest, ComicResponse
  common.py          # MODIFY: new ErrorCodes
  history.py         # MODIFY: new HistoryItem fields
```

### Client Modifications

**LLMClient** (`llm_client.py`):
- Current `chat_with_vision()` requires `image_base64` and `image_format` — cannot be used for text-only calls.
- Add new `chat(system_prompt: str, user_text: str, temperature: float = 0.8) -> str` method for text-only LLM calls (no image in messages payload).
- Existing `chat_with_vision()` stays unchanged for backward compatibility.

**ImageGenClient** (`image_gen_client.py`):
- Current `generate()` requires `image_base64` — this is image-to-image mode.
- Add new `generate_from_text(prompt: str, size: str = "2688*1536") -> str` method for text-to-image mode (no image in DashScope payload, `prompt_extend` set to `false`).
- Existing `generate()` stays unchanged.

### config.py Changes

```python
# Before (old)
app_name: str = "PoseArtGenerator"
poster_storage_dir: str = "data/posters"
photo_storage_dir: str = "data/photos"

# After (new)
app_name: str = "SlangToon"
comic_storage_dir: str = "data/comics"   # renamed from poster_storage_dir
# photo_storage_dir: REMOVED (no photo capture)
```

### FileStorage Changes

- Remove `photo_dir` constructor parameter and `save_photo()` method.
- Rename `poster_dir` parameter to `comic_dir` (or keep generic `storage_dir`).
- `save_poster()` → `save_comic()` (semantic rename).

### LLM Prompt Strategy

**Script Prompt** (`script_prompt.py`):
- Role: Comic scriptwriter + cultural researcher
- Instruction: Pick a random Eastern or Western slang/idiom, explain it in English, write a modern reinterpretation as a 4-6 panel comic script
- Each panel: detailed visual scene description + English dialogue/narration
- Output: structured JSON `{ slang, origin, explanation, panel_count, panels: [{ scene, dialogue }] }`

**Comic Image Prompt** (`comic_prompt.py`):
- Transforms the script panels into a single visual prompt for Qwen Image 2.0
- Specifies: 16:9 layout, panel arrangement (e.g., 4-across or 2x2), manga/comic style, speech bubble positions, color palette, character descriptions per panel
- Output: English prompt string, **max 800 characters** (Qwen Image 2.0 text prompt limit). Must be concise — focus on visual layout and panel descriptions rather than narrative prose.

### Trace Integration

New services integrate with the existing `FlowSession` trace system:
- `script_service.py`: trace step "script_generation" with LLM call duration and token info
- `comic_service.py`: trace step "comic_generation" with prompt and Qwen API call duration

### Error Codes

```python
class ErrorCode:
    BAD_REQUEST = 40001
    SCRIPT_LLM_FAILED = 50001       # Script generation LLM call failed
    SCRIPT_LLM_INVALID = 50002      # Script response JSON parse failed
    COMIC_LLM_FAILED = 50003        # Comic prompt composition failed
    COMIC_LLM_INVALID = 50004       # Comic prompt response parse failed
    IMAGE_GEN_FAILED = 50005        # Qwen Image 2.0 generation failed
    IMAGE_DOWNLOAD_FAILED = 50006   # Image download from Qwen failed
    INTERNAL_ERROR = 50007
```

### Frontend Timeout Configuration

```typescript
TIMEOUTS = {
  SCRIPT_REQUEST: 200_000,   // 200s — LLM text call (no image)
  COMIC_REQUEST: 400_000,    // 400s — Qwen image generation
  HISTORY_REQUEST: 10_000,   // 10s — paginated history
}
```

---

## File Change Summary

### Reuse Without Modification

- `backend/app/main.py` (framework only — routers registered separately)
- `backend/app/dependencies.py`, `middleware.py`, `logging_config.py`
- `backend/app/flow_log/` (trace system)
- `backend/app/services/history_service.py` (CRUD logic unchanged, field names adapted at schema level)
- `frontend/src/hooks/useCamera.ts`, `useMediaPipeHands.ts`, `useGestureDetector.ts`, `useCountdown.ts`
- `frontend/src/utils/gestureAlgo.ts`
- `frontend/src/services/api.ts` (generic `request<T>()` wrapper — add new endpoint functions)
- `frontend/src/components/ErrorDisplay.tsx`, `LoadingSpinner.tsx`

### Modify

- `backend/app/main.py` — register new routers (`script`, `comic`), remove old (`analyze`, `generate`), remove `photo_storage_dir` from lifespan
- `backend/app/config.py` — rename `app_name` to `"SlangToon"`, `poster_storage_dir` → `comic_storage_dir`, remove `photo_storage_dir`
- `backend/app/schemas/common.py` — new ErrorCodes
- `backend/app/schemas/history.py` — new HistoryItem fields (`slang`, `origin`, `explanation`, `panel_count`, `comic_url`, `comic_prompt`; remove `style_name`, `photo_url`)
- `backend/app/services/llm_client.py` — add `chat()` method for text-only calls
- `backend/app/services/image_gen_client.py` — add `generate_from_text()` method for text-to-image
- `backend/app/storage/file_storage.py` — remove `photo_dir`/`save_photo()`, rename poster→comic
- `frontend/src/types/index.ts` — new AppState enum + interfaces (`ScriptData`, `Panel`, `ComicData`)
- `frontend/src/constants/index.ts` — new API endpoints + timeout values
- `frontend/src/App.tsx` — new state machine + component composition
- `CLAUDE.md` — update project name, structure, API docs, error codes

### Delete

- `backend/app/prompts/analyze_prompt.py`, `compose_prompt.py`
- `backend/app/services/analyze_service.py`, `generate_service.py`
- `backend/app/routers/analyze.py`, `generate.py`
- `backend/app/schemas/analyze.py`, `generate.py`
- `frontend/src/components/StyleSelection/`, `StyleCard/`, `PosterDisplay/`, `GestureOverlay/`, `Countdown/`
- `frontend/src/utils/captureFrame.ts`
- `tests/backend/unit/test_analyze.py`, `test_generate.py`, `test_system_prompt.py`, `test_schemas_common.py`
- Frontend tests for deleted components

### New Files

- `backend/app/prompts/script_prompt.py`, `comic_prompt.py`
- `backend/app/services/script_service.py`, `comic_service.py`
- `backend/app/routers/script.py`, `comic.py`
- `backend/app/schemas/script.py`, `comic.py`
- `frontend/src/components/ScriptPreview/ScriptPreview.tsx`
- `frontend/src/components/ComicDisplay/ComicDisplay.tsx`
- `frontend/src/components/HistoryList/HistoryList.tsx` (rewrite)

---

## Testing Strategy

### Reuse

- `tests/backend/conftest.py` fixtures (`client`, `tmp_data_dir`)
- Remove `sample_image_base64` and `mock_image_gen_b64` fixtures (no photo capture, no image-to-image)
- Add new fixtures: `mock_script_response` (mock LLM JSON), `mock_comic_prompt` (mock prompt string)
- Test infrastructure patterns (pytest-asyncio, mock patterns)

### Delete

- `tests/backend/unit/test_analyze.py`, `test_generate.py`, `test_system_prompt.py`, `test_schemas_common.py`
- Frontend tests for deleted components

### New Tests

- `tests/backend/unit/test_script_service.py` — text-only LLM call, JSON parsing, panel_count validation (4-6 range)
- `tests/backend/unit/test_comic_service.py` — prompt assembly, Qwen text-to-image call, prompt length ≤ 800 chars
- `tests/backend/unit/test_script.py` — router integration test (`/api/generate-script`)
- `tests/backend/unit/test_comic.py` — router integration test (`/api/generate-comic`)
- `tests/backend/unit/test_llm_client.py` — extend existing: test new `chat()` method
- `tests/backend/unit/test_image_gen_client.py` — extend existing: test new `generate_from_text()` method
- Frontend unit tests for `ScriptPreview`, `ComicDisplay`, `HistoryList`

---

## Technical Stack (Unchanged)

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript 5.7, Vite 6, Tailwind CSS 4 |
| Backend | FastAPI, Python 3.12 |
| Gesture | MediaPipe Hands |
| LLM | GLM-4.6V (BigModel, OpenAI-compatible) |
| Image Gen | Qwen Image 2.0 (DashScope) |
| Package | `uv` (Python), `npm` (frontend) |
