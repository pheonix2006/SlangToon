# Qwen Image 2.0 Prompt Token Limit Detection + LLM Condense Retry

> Date: 2026-04-03

## Problem

Qwen Image 2.0 has a hard input limit of 1000 tokens. The current `build_comic_prompt()` only enforces a 780-character limit, which does not guarantee the prompt stays within 1000 tokens. Long scene/dialogue descriptions from the LLM can cause the final prompt to exceed this limit, leading to API errors or truncated output.

## Solution

Three-layer approach: **Prevention** (prompt guidance) + **Detection** (tiktoken counting) + **Retry** (LLM condense with algorithmic fallback).

### Layer 1: Prevention — SCRIPT_SYSTEM_PROMPT

Add concise writing guidance to `script_prompt.py` so the LLM generates shorter scripts from the start.

**Change**: Append to `SCRIPT_SYSTEM_PROMPT`:
```
- Keep scene descriptions concise (under 50 words each) and dialogue brief (under 20 words).
  The total comic prompt must be compact enough for image generation.
```

### Layer 2: Detection — tiktoken in comic_prompt.py

**New function** `count_tokens(text, encoding="cl100k_base") -> int` using tiktoken.

**New constant** `MAX_PROMPT_TOKENS = 950` (50-token safety margin).

`build_comic_prompt()` gains a final token-level check after the existing character-level compression. If the prompt exceeds `MAX_PROMPT_TOKENS`, it returns the prompt as-is (the retry logic in comic_service handles it).

### Layer 3: Retry — comic_service.py

`generate_comic()` flow becomes:

```
build_comic_prompt() → count_tokens()
  → within limit: proceed to image generation
  → exceeds limit: call LLM to condense script_data → rebuild prompt → recheck
    → still exceeds (max 2 retries): algorithmic truncation fallback
```

**New file**: `backend/app/prompts/condense_prompt.py` containing `CONDENSE_SYSTEM_PROMPT`.

```python
CONDENSE_SYSTEM_PROMPT = """You are a comic script editor. Shorten the given comic script's
scene and dialogue text while preserving the story's core narrative and emotional arc.

Rules:
- Reduce each scene to under 30 words
- Reduce each dialogue to under 12 words
- Keep slang, origin, explanation unchanged
- Maintain the same panel_count
- Return the same JSON format"""
```

**Retry logic in `comic_service.py`**:
- Max 2 condense retries
- Each retry calls `llm.chat(CONDENSE_SYSTEM_PROMPT, script_json, temperature=0.3)`
- Parses condensed JSON, validates structure, rebuilds prompt
- If LLM condense fails (timeout, parse error), falls back to algorithmic truncation
- If all retries exhausted, forces token-level truncation as last resort

## Files Changed

| File | Change |
|------|--------|
| `backend/app/prompts/script_prompt.py` | Add conciseness guidance |
| `backend/app/prompts/condense_prompt.py` | **New** — condense prompt template |
| `backend/app/prompts/comic_prompt.py` | Add `count_tokens()`, `MAX_PROMPT_TOKENS` |
| `backend/app/services/comic_service.py` | Token detection + condense retry loop |
| `pyproject.toml` | Add `tiktoken` dependency |
| `tests/backend/unit/test_comic_service.py` | Update for retry logic |
| `tests/backend/unit/test_prompts.py` | Add token count tests |

## Error Handling

- Condense LLM call fails → fall back to algorithmic truncation
- 2 retries exhausted → force token-level truncation
- No new error codes — log warnings via existing logger

## Dependencies

- `tiktoken` — added to `pyproject.toml`
