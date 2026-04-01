# Test Coverage Design — Pose Art Generator

Date: 2026-03-29
Status: Approved

## Overview

Full coverage of all missing unit, integration, and E2E tests across backend, frontend, and end-to-end layers. The approach follows the test pyramid: unit tests form the broad base, integration tests the middle, and E2E tests the narrow top.

**Current state:**
- Backend: 39/39 unit tests pass. Gaps in config, main, schemas, dependencies, and some service edge cases.
- Frontend: Zero tests. No framework, no config, no files.
- E2E: One backend-only script (`e2e_test.py`). No browser-based E2E tests.

**Target state:**
- Backend: ~60 tests (add ~20)
- Frontend: ~60 tests (from zero)
- E2E: 20 Playwright tests + 4 enhanced backend E2E scenarios

## Tools

| Layer | Tool | Purpose |
|-------|------|---------|
| Backend unit | pytest + unittest.mock | Already configured |
| Frontend unit/integration | Vitest + @testing-library/react + jsdom | New setup |
| Browser E2E | Playwright | New setup |
| Backend E2E | httpx + existing e2e_test.py | Enhanced |

## 1. Backend Unit Test Supplements (~20 new tests)

### 1.1 `test_config.py` — Settings & Configuration (5 tests)

| Test | Description |
|------|-------------|
| `test_settings_default_values` | Verify default host=0.0.0.0, port=8888, debug=False |
| `test_settings_from_env` | Override config values via environment variables |
| `test_settings_validation_invalid_port` | Invalid port raises ValidationError |
| `test_get_settings_caching` | `get_settings()` returns singleton |
| `test_cors_origin_list` | `cors_origin_list` property parses correctly |

### 1.2 `test_app.py` — Application Factory (5 tests)

| Test | Description |
|------|-------------|
| `test_create_app_returns_fastapi` | Returns FastAPI instance |
| `test_health_endpoint` | GET /health returns 200 with expected body |
| `test_cors_middleware_configured` | CORSMiddleware present with correct origins |
| `test_static_files_mounted` | /data path serves static files |
| `test_routers_registered` | All 3 routers registered (/api/analyze, /api/generate, /api/history) |

### 1.3 `test_schemas_common.py` — Common Schemas (6 tests)

| Test | Description |
|------|-------------|
| `test_api_response_success` | code=0 response serialization |
| `test_api_response_error` | code!=0 error response |
| `test_error_response_fields` | ErrorResponse has message and code |
| `test_error_code_values` | ErrorCode constants match expected values |
| `test_history_item_optional_fields` | HistoryItem optional fields default correctly |
| `test_history_response_serialization` | HistoryResponse includes items/total/page/page_size/total_pages |

### 1.4 `test_dependencies.py` — Dependency Injection (2 tests)

| Test | Description |
|------|-------------|
| `test_get_cached_settings_returns_settings` | Returns Settings instance |
| `test_get_cached_settings_same_instance` | LRUCache returns same instance |

### 1.5 `test_system_prompt.py` — System Prompt Validation (3 tests)

| Test | Description |
|------|-------------|
| `test_system_prompt_contains_all_styles` | All 10 art styles present |
| `test_system_prompt_contains_json_format_requirement` | JSON output format requirement present |
| `test_system_prompt_is_valid_string` | Non-empty string, correct type |

### 1.6 `test_generate_service.py` — Generate Service Edge Cases (2 tests, additions)

| Test | Description |
|------|-------------|
| `test_generate_artwork_download_failure` | `_download_as_base64` failure throws error code 50004 |
| `test_generate_artwork_photo_save_failure` | Photo save failure handled correctly |

## 2. Frontend Unit & Integration Tests (~60 new tests)

### 2.0 Infrastructure Setup

- **Dependencies**: vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom
- **Config**: `vitest.config.ts` with jsdom environment, path aliases, setup file
- **Setup**: `src/test/setup.ts` with jest-dom matchers and global mocks (fetch, navigator.mediaDevices, ResizeObserver, HTMLCanvasElement)
- **Scripts**: `test`, `test:watch`, `test:coverage`
- **Test image fixture**: `src/test/fixtures/test-person.jpg` — a downloaded person image for simulating camera captures

### 2.1 Pure Function Tests

#### `utils/gestureAlgo.test.ts` (10 tests)

| Test | Description |
|------|-------------|
| `test_ok_gesture_detected` | Normal OK gesture returns `{ gesture: 'ok', confidence > 0.8 }` |
| `test_ok_gesture_boundary_distance` | Distance at threshold boundary (0.06) |
| `test_open_palm_detected` | All 5 fingers extended returns `{ gesture: 'open_palm' }` |
| `test_open_palm_partial_fingers` | Some fingers bent — not detected as palm |
| `test_no_gesture` | Random hand positions returns `{ gesture: 'none' }` |
| `test_empty_landmarks` | Empty array returns `{ gesture: 'none', confidence: 0 }` |
| `test_single_point` | Single landmark returns `{ gesture: 'none' }` |
| `test_all_zero_landmarks` | All coordinates zero returns `{ gesture: 'none' }` |
| `test_confidence_range` | Confidence always between 0 and 1 |
| `test_ok_with_other_fingers_curled` | OK sign: thumb+index close, others curled |

#### `utils/captureFrame.test.ts` (5 tests)

| Test | Description |
|------|-------------|
| `test_capture_returns_base64_string` | Returns non-empty base64 string |
| `test_capture_uses_jpeg_format` | Canvas toDataURL called with 'image/jpeg' |
| `test_capture_strips_data_prefix` | Output does not contain 'data:image' prefix |
| `test_capture_empty_video` | Video with no frame returns empty string |
| `test_capture_quality_parameter` | Quality 0.85 passed to toDataURL |

### 2.2 Service Layer Tests

#### `services/api.test.ts` (12 tests)

Mock `global.fetch` for all tests.

| Test | Description |
|------|-------------|
| `analyzePhoto_success` | POST /api/analyze with correct snake_case fields, returns parsed options |
| `analyzePhoto_network_error` | Network failure throws friendly error message |
| `analyzePhoto_timeout` | Timeout triggers TimeoutError |
| `analyzePhoto_business_error` | code !== 0 in response throws ApiError |
| `generatePoster_success` | POST /api/generate with correct fields, returns poster data |
| `generatePoster_network_error` | Network failure |
| `generatePoster_timeout` | Timeout handling |
| `generatePoster_business_error` | code !== 0 handling |
| `getHistory_success` | GET /api/history with correct query params |
| `getHistory_network_error` | Network failure |
| `getHistory_timeout` | Timeout handling |
| `request_content_type` | Request has Content-Type: application/json header |

### 2.3 Custom Hook Tests

#### `hooks/useCountdown.test.ts` (6 tests)

| Test | Description |
|------|-------------|
| `test_counts_down_from_initial` | Decrements every second |
| `test_calls_onComplete_at_zero` | Triggers callback when reaching 0 |
| `test_does_not_decrement_when_inactive` | active=false stops countdown |
| `test_reset_restarts_countdown` | reset() restores initial value |
| `test_cleanup_on_unmount` | Timer cleared on unmount |
| `test_stable_callback_ref` | Callback ref avoids stale closures |

#### `hooks/useGestureDetector.test.ts` (6 tests)

| Test | Description |
|------|-------------|
| `test_ok_gesture_triggers_after_threshold` | Fires after 8 consecutive OK frames |
| `test_palm_gesture_triggers_after_threshold` | Fires after 5 consecutive palm frames |
| `test_gesture_change_resets_counter` | Switching gesture resets count |
| `test_below_threshold_no_trigger` | 7 OK frames (below 8) does not trigger |
| `test_trigger_resets_counter` | After triggering, counter resets |
| `test_none_gesture_resets` | 'none' gesture resets accumulated count |

#### `hooks/useCamera.test.ts` (5 tests)

| Test | Description |
|------|-------------|
| `test_successful_camera_init` | getUserMedia called with correct constraints |
| `test_not_allowed_error` | NotAllowedError sets error state |
| `test_not_found_error` | NotFoundError sets error state |
| `test_restart_reinitializes` | restart() calls getUserMedia again |
| `test_cleanup_on_unmount` | Stream tracks stopped on unmount |

#### `hooks/useMediaPipeHands.test.ts` (4 tests)

| Test | Description |
|------|-------------|
| `test_hands_initialized_with_correct_params` | maxNumHands=1, modelComplexity=1 |
| `test_sends_frames_to_callback` | onResults called with landmarks |
| `test_canvas_draws_landmarks` | Canvas context draw operations called |
| `test_cleanup_on_unmount` | Hands model closed on unmount |

### 2.4 Component Tests

#### `components/ErrorDisplay.test.tsx` (4 tests)

| Test | Description |
|------|-------------|
| `test_displays_error_message` | Error text visible |
| `test_retry_button_shown_when_handler_provided` | Button rendered with onRetry |
| `test_retry_button_click_calls_handler` | Click triggers onRetry |
| `test_no_retry_button_without_handler` | Button hidden when onRetry not provided |

#### `components/LoadingSpinner.test.tsx` (3 tests)

| Test | Description |
|------|-------------|
| `test_renders_with_default_size` | Default md size |
| `test_renders_all_sizes` | sm/md/lg sizes applied |
| `test_displays_optional_text` | Text displayed when provided |

#### `components/StyleCard/StyleCard.test.tsx` (4 tests)

| Test | Description |
|------|-------------|
| `test_displays_name_and_brief` | Name and description text visible |
| `test_selected_state_style` | Selected prop applies cyan border |
| `test_click_calls_onSelect` | Click triggers onSelect with name |
| `test_hover_effect` | Cursor pointer on hover |

#### `components/Countdown/Countdown.test.tsx` (3 tests)

| Test | Description |
|------|-------------|
| `test_displays_number` | Large number visible |
| `test_hidden_when_zero` | Not rendered when remaining <= 0 |
| `test_pulse_animation` | Ping/pulse CSS classes applied |

#### `components/GestureOverlay/GestureOverlay.test.tsx` (4 tests)

| Test | Description |
|------|-------------|
| `test_ok_gesture_green_highlight` | Green style for 'ok' |
| `test_palm_gesture_green_highlight` | Green style for 'open_palm' |
| `test_none_gesture_gray_style` | Gray style for 'none' |
| `test_confidence_percentage_displayed` | Confidence shown as percentage |

#### `components/StyleSelection/StyleSelection.test.tsx` (4 tests)

| Test | Description |
|------|-------------|
| `test_renders_style_cards` | 3 cards rendered in grid |
| `test_loading_state` | Loading spinner when loading=true |
| `test_error_state` | Error display when error set |
| `test_select_triggers_callback` | Card click fires onSelect |

#### `components/HistoryList/HistoryList.test.tsx` (4 tests)

| Test | Description |
|------|-------------|
| `test_empty_state` | Placeholder shown when no items |
| `test_list_view` | Grid of history items displayed |
| `test_detail_view_on_click` | Clicking item switches to detail view |
| `test_back_button_returns_to_list` | Back button returns to list view |

#### `components/PosterDisplay/PosterDisplay.test.tsx` (5 tests)

| Test | Description |
|------|-------------|
| `test_displays_poster_image` | Poster image rendered |
| `test_download_button` | Click triggers download via anchor element |
| `test_regenerate_button` | Click calls onRegenerate |
| `test_retake_button` | Click calls onRetake |
| `test_loading_overlay` | Loading spinner when generating |

#### `components/CameraView/CameraView.test.tsx` (3 tests)

| Test | Description |
|------|-------------|
| `test_renders_video_element` | Video element present |
| `test_mirror_transform` | scaleX(-1) CSS applied |
| `test_canvas_overlay` | Canvas element for landmarks overlay |

## 3. Playwright E2E Tests (20 tests)

### 3.0 Infrastructure Setup

- **Dependencies**: @playwright/test
- **Config**: `frontend/playwright.config.ts`
  - baseURL: http://localhost:5173
  - webServer: auto-start backend (port 8888) and frontend (port 5173)
  - timeout: 60s (API calls are slow)
- **Fixtures**: `frontend/e2e/fixtures/test-person.jpg` — downloaded person image for camera simulation
- **Support files**: `frontend/e2e/support/` — custom fixtures for camera mock, API mock, gesture simulation

### 3.1 Mock Strategy

| Target | Method |
|--------|--------|
| Camera (getUserMedia) | Inject script to override navigator.mediaDevices, return test video stream from fixture image |
| MediaPipe CDN | Mock WASM/model file routes to prevent CDN dependency |
| Gesture detection | Inject test landmarks into the detection pipeline, bypass real MediaPipe |
| Backend API (/api/analyze) | page.route() mock returning 3 style options |
| Backend API (/api/generate) | page.route() mock returning poster base64 |
| File download | Listen for download event, verify trigger |
| History API (/api/history) | page.route() mock returning sample records |

### 3.2 Test Cases

#### Core Flow (15 tests)

| # | Test | Spec | Description |
|---|------|------|-------------|
| 1 | `app-loads-successfully` | F.1 | App loads without white screen, camera view visible |
| 2 | `camera-initializes` | F.2 | Front camera starts, video element has stream |
| 3 | `gesture-overlay-visible` | F.4 | Bottom gesture overlay displays current state |
| 4 | `ok-gesture-triggers-countdown` | F.3,F.5 | Injecting OK landmarks triggers 3s countdown |
| 5 | `countdown-3-2-1` | F.5 | Countdown displays 3, 2, 1 sequentially |
| 6 | `analyze-api-called` | F.6 | After countdown, /api/analyze called with base64 payload |
| 7 | `style-options-displayed` | F.7 | 3 style cards shown after analysis |
| 8 | `style-card-selectable` | F.8 | Clicking card highlights it with cyan border |
| 9 | `generate-api-called` | F.9 | Selecting style calls /api/generate |
| 10 | `poster-displayed` | F.10 | Generated poster image visible |
| 11 | `download-poster` | F.11 | Download button triggers file save |
| 12 | `regenerate-returns-to-styles` | F.12 | Regenerate shows loading then new poster |
| 13 | `retake-returns-to-camera` | F.13 | Retake returns to camera view |
| 14 | `history-view` | F.14 | History button shows past generations |
| 15 | `open-palm-cancels` | F.3 | Open palm gesture during countdown returns to camera |

#### Error Handling (3 tests)

| # | Test | Spec | Description |
|---|------|------|-------------|
| 16 | `analyze-error-retry` | F.15 | Mock analyze error shows ErrorDisplay with retry |
| 17 | `generate-error-handled` | F.15 | Mock generate error shows error message |
| 18 | `camera-permission-denied` | F.16 | Denied permission shows permission prompt |

#### Other (2 tests)

| # | Test | Spec | Description |
|---|------|------|-------------|
| 19 | `responsive-mobile-layout` | F.17 | Viewport 375px renders correctly |
| 20 | `no-console-errors` | F.18 | Full flow produces zero console errors |

### 3.3 Enhanced Backend E2E (4 additions to e2e_test.py)

| Test | Description |
|------|-------------|
| `test_concurrent_requests` | Multiple concurrent analyze requests don't crash |
| `test_large_image_handling` | Large image (>5MB base64) handled gracefully |
| `test_history_pagination_edge_cases` | Boundary pagination (page 0, page_size max, etc.) |
| `test_invalid_base64_handling` | Non-base64 string returns appropriate error |

## 4. Test Execution

### Running Tests

```bash
# Backend unit tests
uv run pytest backend/tests/ -v --ignore=backend/tests/test_real_api.py

# Backend real API tests (requires running services)
uv run python backend/tests/test_real_api.py

# Frontend unit/integration tests
cd frontend && npm test

# Frontend tests with coverage
cd frontend && npm run test:coverage

# Playwright E2E tests (requires no running servers, auto-starts)
cd frontend && npx playwright test

# Backend E2E tests (requires running backend)
uv run python e2e_test.py
```

### CI Integration (future)

All tests except `test_real_api.py` and backend E2E should run without external services. Playwright tests mock all external dependencies.
