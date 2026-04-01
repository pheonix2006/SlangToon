# SlangToon — Slang-to-Comic Generator Design

> Date: 2026-04-01
> Status: Approved

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

---

## API Design

### `POST /api/generate-script`

Generate a random slang with comic script.

**Request**: Empty body `{}`

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
  "panels": [
    { "scene": "...", "dialogue": "..." }
  ]
}
```

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

**Image spec**: 16:9 aspect ratio (1024x576), single image with multi-panel comic layout (borders, speech bubbles, panel dividers).

### `GET /api/history` (unchanged)

Paginated history of generated comics. Same pagination structure as existing, field names adapted for comic data.

### `GET /health` (unchanged)

---

## Backend Architecture

### New Service Layer

```
routers/
  script.py          → script_service.py → llm_client.py
  comic.py           → comic_service.py  → llm_client.py + image_gen_client.py
  history.py         → history_service.py (adapted fields)

services/
  script_service.py  # Single LLM call: slang + panels
  comic_service.py   # Build image prompt from panels → Qwen Image 2.0
  llm_client.py      # REUSED (OpenAI-compatible, fully generic)
  image_gen_client.py # REUSED (DashScope Qwen Image 2.0)
  history_service.py # REUSED (field adaptation)

prompts/
  script_prompt.py   # New: instruct LLM to generate slang + comic script JSON
  comic_prompt.py    # New: build visual prompt for multi-panel 16:9 comic

schemas/
  script.py          # ScriptResponse, Panel, SlangData
  comic.py           # ComicRequest, ComicResponse
  common.py          # REUSED ApiResponse + new ErrorCodes
  history.py         # Adapted for comic entries
```

### LLM Prompt Strategy

**Script Prompt** (`script_prompt.py`):
- Role: Comic scriptwriter + cultural researcher
- Instruction: Pick a random Eastern or Western slang/idiom, explain it in English, write a modern reinterpretation as a 4-6 panel comic script
- Each panel: detailed visual scene description + English dialogue/narration
- Output: structured JSON `{ slang, origin, explanation, panel_count, panels: [{ scene, dialogue }] }`

**Comic Image Prompt** (`comic_prompt.py`):
- Transforms the script panels into a single visual prompt for Qwen Image 2.0
- Specifies: 16:9 layout, panel arrangement (e.g., 4-across or 2x2), manga/comic style, speech bubble positions, color palette, character descriptions per panel
- Output: English prompt string (200-500 words) passed directly to Qwen

### Error Codes

```python
class ErrorCode:
    BAD_REQUEST = 40001
    SCRIPT_LLM_FAILED = 50001       # Script generation LLM call failed
    SCRIPT_LLM_INVALID = 50002      # Script response JSON parse failed
    COMIC_LLM_FAILED = 50003        # Comic prompt composition LLM failed
    COMIC_LLM_INVALID = 50004       # Comic prompt response parse failed
    IMAGE_GEN_FAILED = 50005        # Qwen Image 2.0 generation failed
    IMAGE_DOWNLOAD_FAILED = 50006   # Image download from Qwen failed
    INTERNAL_ERROR = 50007
```

---

## File Change Summary

### Reuse Without Modification

- `backend/app/main.py` (framework), `config.py`, `dependencies.py`, `middleware.py`, `logging_config.py`
- `backend/app/flow_log/` (trace system)
- `backend/app/storage/file_storage.py` (file storage + thumbnails)
- `backend/app/services/llm_client.py` (generic OpenAI-compatible client)
- `backend/app/services/image_gen_client.py` (DashScope Qwen client)
- `frontend/src/hooks/useCamera.ts`, `useMediaPipeHands.ts`, `useGestureDetector.ts`, `useCountdown.ts`
- `frontend/src/utils/gestureAlgo.ts`
- `frontend/src/services/api.ts` (generic request wrapper)
- `frontend/src/components/ErrorDisplay.tsx`, `LoadingSpinner.tsx`

### Delete

- `backend/app/prompts/analyze_prompt.py`, `compose_prompt.py`
- `backend/app/services/analyze_service.py`, `generate_service.py`
- `backend/app/routers/analyze.py`, `generate.py`
- `backend/app/schemas/analyze.py`, `generate.py`
- `frontend/src/components/StyleSelection/`, `StyleCard/`, `PosterDisplay/`, `GestureOverlay/`, `Countdown/`
- `frontend/src/utils/captureFrame.ts`

### New Files

- `backend/app/prompts/script_prompt.py`, `comic_prompt.py`
- `backend/app/services/script_service.py`, `comic_service.py`
- `backend/app/routers/script.py`, `comic.py`
- `backend/app/schemas/script.py`, `comic.py`
- `frontend/src/components/ScriptPreview/ScriptPreview.tsx`
- `frontend/src/components/ComicDisplay/ComicDisplay.tsx`
- `frontend/src/components/HistoryList/HistoryList.tsx` (rewrite)

### Modify

- `backend/app/main.py` — register new routers, remove old
- `backend/app/config.py` — clean up unused fields
- `backend/app/schemas/common.py` — new ErrorCodes
- `frontend/src/types/index.ts` — new AppState enum + interfaces
- `frontend/src/constants/index.ts` — new API endpoints
- `frontend/src/App.tsx` — new state machine + component composition

---

## Testing Strategy

### Reuse

- `tests/backend/conftest.py` fixtures (`client`, `tmp_data_dir`, `sample_image_base64` — latter no longer needed)
- Test infrastructure patterns (pytest-asyncio, mock patterns)

### Delete

- `tests/backend/unit/test_analyze.py`, `test_generate.py`, `test_system_prompt.py`
- `tests/backend/unit/test_schemas_common.py` (old schemas)
- Frontend tests for deleted components

### New Tests

- `tests/backend/unit/test_script_service.py` — LLM call, JSON parsing, panel_count validation
- `tests/backend/unit/test_comic_service.py` — prompt assembly, Qwen API call, image handling
- `tests/backend/unit/test_script.py` — router integration test (`/api/generate-script`)
- `tests/backend/unit/test_comic.py` — router integration test (`/api/generate-comic`)
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
