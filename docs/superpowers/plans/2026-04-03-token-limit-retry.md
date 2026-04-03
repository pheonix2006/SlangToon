# Qwen Image 2.0 Token Limit Detection + LLM Condense Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add token-level detection and LLM-powered condense retry to prevent Qwen Image 2.0 prompt overflow.

**Architecture:** Three-layer approach — prevention (prompt brevity guidance), detection (tiktoken counting), retry (LLM condense with algorithmic truncation fallback). Token check runs after `build_comic_prompt()` in `comic_service.py`, with up to 2 LLM condense retries before force-truncating.

**Tech Stack:** tiktoken (new dependency), existing LLMClient for condense calls

---

### Task 1: Add tiktoken dependency + count_tokens + MAX_PROMPT_TOKENS

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/app/prompts/comic_prompt.py`
- Test: `tests/backend/unit/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/backend/unit/test_prompts.py` 文件末尾追加以下测试类：

```python
class TestCountTokens:
    def test_count_tokens_basic(self):
        """count_tokens should return a positive integer for non-empty text."""
        from app.prompts.comic_prompt import count_tokens

        result = count_tokens("Hello, world!")
        assert isinstance(result, int)
        assert result > 0

    def test_count_tokens_empty(self):
        """count_tokens should return 0 for empty string."""
        from app.prompts.comic_prompt import count_tokens

        assert count_tokens("") == 0

    def test_count_tokens_approximate_accuracy(self):
        """count_tokens result should be roughly proportional to text length."""
        from app.prompts.comic_prompt import count_tokens

        short = count_tokens("cat")
        long = count_tokens("The quick brown fox jumps over the lazy dog " * 10)
        assert 0 < short < long

    def test_count_tokens_custom_encoding(self):
        """count_tokens should accept a custom encoding_name parameter."""
        from app.prompts.comic_prompt import count_tokens

        result = count_tokens("Hello", encoding_name="p50k_base")
        assert isinstance(result, int)
        assert result > 0


class TestMaxPromptTokensConstant:
    def test_max_prompt_tokens_value(self):
        """MAX_PROMPT_TOKENS should be 950 (1000 - 50 safety margin)."""
        from app.prompts.comic_prompt import MAX_PROMPT_TOKENS

        assert MAX_PROMPT_TOKENS == 950

    def test_max_prompt_tokens_less_than_hard_limit(self):
        """MAX_PROMPT_TOKENS must be strictly less than Qwen's 1000-token hard limit."""
        from app.prompts.comic_prompt import MAX_PROMPT_TOKENS

        assert MAX_PROMPT_TOKENS < 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_prompts.py::TestCountTokens tests/backend/unit/test_prompts.py::TestMaxPromptTokensConstant -v`

Expected: FAIL — `ImportError: cannot import name 'count_tokens' from 'app.prompts.comic_prompt'` and `ImportError: cannot import name 'MAX_PROMPT_TOKENS' from 'app.prompts.comic_prompt'`

- [ ] **Step 3: Write minimal implementation**

**3a.** 在 `pyproject.toml` 的 `dependencies` 列表中添加 `tiktoken`：

```toml
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "httpx>=0.27.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "Pillow>=10.2.0",
    "python-multipart>=0.0.9",
    "langsmith>=0.1.0",
    "tiktoken>=0.7.0",
]
```

**3b.** 在 `backend/app/prompts/comic_prompt.py` 顶部添加 `import tiktoken`，在 `MAX_PROMPT_LENGTH = 780` 之后添加 `MAX_PROMPT_TOKENS` 和 `count_tokens` 函数：

```python
"""Build visual prompt for Qwen Image 2.0 from comic script data."""

import tiktoken

# Qwen Image 2.0 text field hard limit: 800 characters.
# API auto-truncates anything beyond this. Leave 20-char safety margin.
MAX_PROMPT_LENGTH = 780

# Qwen Image 2.0 token hard limit: 1000 tokens.
# Leave 50-token safety margin to avoid truncation.
MAX_PROMPT_TOKENS = 950


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in text using tiktoken.

    Args:
        text: The string to tokenize.
        encoding_name: tiktoken encoding name. Defaults to "cl100k_base".

    Returns:
        Token count as integer. Returns 0 for empty strings.
    """
    if not text:
        return 0
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


# ... (rest of existing functions unchanged: _get_layout, _build_panel_lines, build_comic_prompt)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/backend/unit/test_prompts.py -v`

Expected: ALL PASS — 原有的 `TestBuildComicPrompt` 和 `TestScriptPrompt` 全部通过，新增的 `TestCountTokens`（4 个测试）和 `TestMaxPromptTokensConstant`（2 个测试）也通过。

- [ ] **Step 5: Install tiktoken dependency**

Run: `uv sync`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock backend/app/prompts/comic_prompt.py tests/backend/unit/test_prompts.py
git commit -m "feat(comic_prompt): add tiktoken count_tokens and MAX_PROMPT_TOKENS constant

Add tiktoken dependency for token counting. Introduce count_tokens()
utility and MAX_PROMPT_TOKENS=950 constant (Qwen 1000-token limit minus
50 safety margin). No changes to build_comic_prompt logic."
```

---

### Task 2: Update SCRIPT_SYSTEM_PROMPT + Create condense_prompt.py

**Files:**
- Modify: `backend/app/prompts/script_prompt.py`
- Create: `backend/app/prompts/condense_prompt.py`
- Test: `tests/backend/unit/test_prompts.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/backend/unit/test_prompts.py` 中：

1. 在文件顶部添加导入：`from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT`
2. 更新 `TestScriptPrompt.test_prompt_contains_key_instructions`，追加断言：
```python
def test_prompt_contains_key_instructions(self):
    assert "JSON" in SCRIPT_SYSTEM_PROMPT
    assert "8-12" in SCRIPT_SYSTEM_PROMPT
    assert "Eastern" in SCRIPT_SYSTEM_PROMPT
    assert "Western" in SCRIPT_SYSTEM_PROMPT
    assert "English" in SCRIPT_SYSTEM_PROMPT
    # New: verify brevity rules
    assert "concise" in SCRIPT_SYSTEM_PROMPT
    assert "50 words" in SCRIPT_SYSTEM_PROMPT
    assert "20 words" in SCRIPT_SYSTEM_PROMPT
    assert "Brevity is critical" in SCRIPT_SYSTEM_PROMPT
```

3. 在 `TestScriptPrompt` 和 `TestBuildComicPrompt` 之间新增 `TestCondensePrompt` 类：

```python
class TestCondensePrompt:
    def test_prompt_exists_and_non_empty(self):
        assert CONDENSE_SYSTEM_PROMPT is not None
        assert len(CONDENSE_SYSTEM_PROMPT) > 0

    def test_prompt_contains_role_definition(self):
        assert "comic script editor" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_contains_condensing_rules(self):
        assert "30 words" in CONDENSE_SYSTEM_PROMPT
        assert "12 words" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_preserves_structure(self):
        assert "slang" in CONDENSE_SYSTEM_PROMPT
        assert "origin" in CONDENSE_SYSTEM_PROMPT
        assert "explanation" in CONDENSE_SYSTEM_PROMPT
        assert "panel_count" in CONDENSE_SYSTEM_PROMPT

    def test_prompt_requests_json_response(self):
        assert "JSON" in CONDENSE_SYSTEM_PROMPT
        assert "same format" in CONDENSE_SYSTEM_PROMPT
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_prompts.py -v`

Expected: FAIL — `ImportError: cannot import name 'CONDENSE_SYSTEM_PROMPT'` 和 4 个新断言失败 (`"concise"`, `"50 words"`, `"20 words"`, `"Brevity is critical"`)

- [ ] **Step 3: Write minimal implementation**

**文件 1: 修改 `backend/app/prompts/script_prompt.py`**

在 `IMPORTANT RULES` 末尾（`- Do NOT pick modern internet slang, memes, or trendy expressions` 之后）添加两条新规则：

```
- Keep scene descriptions concise (under 50 words each) and dialogue brief (under 20 words). The total comic prompt must be compact enough for image generation.
- Brevity is critical: shorter descriptions lead to better image generation results
```

**文件 2: 新建 `backend/app/prompts/condense_prompt.py`**

```python
"""Prompt template for condensing comic scripts that exceed token limits."""

CONDENSE_SYSTEM_PROMPT = """\
You are a comic script editor. Your task is to shorten the given comic script's \
scene and dialogue text while preserving the story's core narrative and emotional arc.

Rules:
- Reduce each scene description to under 30 words
- Reduce each dialogue to under 12 words
- Keep the slang, origin, explanation fields unchanged
- Maintain the same panel_count
- Return the exact same JSON format

You MUST respond with a JSON object in the same format you received.
"""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/backend/unit/test_prompts.py -v`

Expected: PASS — 全部测试通过，包括更新后的 `TestScriptPrompt` 和新增的 `TestCondensePrompt`。

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompts/script_prompt.py backend/app/prompts/condense_prompt.py tests/backend/unit/test_prompts.py
git commit -m "feat(prompts): add brevity rules to SCRIPT_SYSTEM_PROMPT and create CONDENSE_SYSTEM_PROMPT

- Add scene (under 50 words) and dialogue (under 20 words) brevity rules
- Create condense_prompt.py with CONDENSE_SYSTEM_PROMPT for token-limit retry
- Update test_prompts.py with brevity assertions and TestCondensePrompt class"
```

---

### Task 3: Add token detection + LLM condense retry in comic_service.py

**Files:**
- Modify: `backend/app/services/comic_service.py`
- Modify: `backend/app/prompts/comic_prompt.py` (添加 `_truncate_prompt_to_tokens`)
- Test: `tests/backend/unit/test_comic_service.py`

- [ ] **Step 1: Write the failing tests**

在 `tests/backend/unit/test_comic_service.py` 文件顶部确保有 `import json`，在文件末尾追加：

```python
class TestTokenCondenseRetry:
    """Tests for token detection + LLM condense retry logic."""

    @pytest.mark.asyncio
    async def test_prompt_within_token_limit(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """Normal flow: prompt within MAX_PROMPT_TOKENS, no condense needed."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )
        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        with patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        mock_img_client.generate_from_text.assert_called_once()
        # Verify prompt passed to image gen is within token limit
        call_args = mock_img_client.generate_from_text.call_args
        prompt_arg = call_args.kwargs["prompt"]
        from app.prompts.comic_prompt import count_tokens, MAX_PROMPT_TOKENS
        assert count_tokens(prompt_arg) <= MAX_PROMPT_TOKENS

    @pytest.mark.asyncio
    async def test_condense_retry_on_token_overflow(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """Prompt exceeds token limit -> LLM condense called -> condensed prompt used."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        # Build a condensed version that the mock LLM will return
        condensed_panels = [
            {**p, "scene": p["scene"][:20], "dialogue": p["dialogue"][:10]}
            for p in mock_script_data["panels"]
        ]
        condensed_json = json.dumps({
            "slang": mock_script_data["slang"],
            "origin": mock_script_data["origin"],
            "explanation": mock_script_data["explanation"],
            "panel_count": mock_script_data["panel_count"],
            "panels": condensed_panels,
        })

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=condensed_json)

        with (
            patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
            patch("app.services.comic_service.LLMClient", return_value=mock_llm),
            patch("app.services.comic_service.count_tokens", side_effect=[1200, 500]),
        ):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        mock_llm.chat.assert_called_once()
        from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
        call_args = mock_llm.chat.call_args
        assert call_args.kwargs["system_prompt"] == CONDENSE_SYSTEM_PROMPT
        assert call_args.kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_condense_fallback_on_llm_failure(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """LLM condense fails -> fallback to truncation, no exception raised."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        from app.services.llm_client import LLMTimeoutError
        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(side_effect=LLMTimeoutError("timeout"))

        # Token counts: first check=1200 (over), after truncation=500 (ok)
        with (
            patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
            patch("app.services.comic_service.LLMClient", return_value=mock_llm),
            patch("app.services.comic_service.count_tokens", side_effect=[1200, 500]),
        ):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        mock_img_client.generate_from_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_condense_exhausted_max_retries(
        self, mock_script_data, mock_image_gen_b64, tmp_data_dir
    ):
        """2 retries still over token limit -> force truncation as last resort."""
        settings = _make_settings(
            comic_storage_dir=str(tmp_data_dir / "comics"),
            history_file=str(tmp_data_dir / "history.json"),
        )

        # Condensed script that is STILL over limit after each retry
        still_long_panels = [
            {**p, "scene": p["scene"] + " padding " * 50, "dialogue": p["dialogue"]}
            for p in mock_script_data["panels"]
        ]
        still_long_json = json.dumps({
            "slang": mock_script_data["slang"],
            "origin": mock_script_data["origin"],
            "explanation": mock_script_data["explanation"],
            "panel_count": mock_script_data["panel_count"],
            "panels": still_long_panels,
        })

        mock_img_client = MagicMock(spec=ImageGenClient)
        mock_img_client.generate_from_text = AsyncMock(return_value=mock_image_gen_b64)

        mock_llm = MagicMock()
        mock_llm.chat = AsyncMock(return_value=still_long_json)

        # Token counts: initial=1200, after retry1=1100, after retry2=1050, after truncate=500
        with (
            patch("app.services.comic_service.ImageGenClient", return_value=mock_img_client),
            patch("app.services.comic_service.LLMClient", return_value=mock_llm),
            patch("app.services.comic_service.count_tokens", side_effect=[1200, 1100, 1050, 500]),
        ):
            result = await generate_comic(mock_script_data, settings)

        assert "comic_url" in result
        assert mock_llm.chat.call_count == 2
        mock_img_client.generate_from_text.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/backend/unit/test_comic_service.py::TestTokenCondenseRetry -v`

Expected: FAIL — `generate_comic` 尚未包含 token 检测和 condense 重试逻辑，`LLMClient` 未被导入到 `comic_service`，`count_tokens` 未被导入。

- [ ] **Step 3: Write minimal implementation**

**3a. 在 `backend/app/prompts/comic_prompt.py` 末尾添加截断辅助函数**

```python
def _truncate_prompt_to_tokens(text: str, max_tokens: int, encoding_name: str = "cl100k_base") -> str:
    """Truncate text to fit within max_tokens by encoding then decoding."""
    enc = tiktoken.get_encoding(encoding_name)
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return enc.decode(truncated_tokens)
```

**3b. 完整替换 `backend/app/services/comic_service.py`**

```python
"""Comic generation service — build prompt + Qwen Image 2.0."""

import json
import logging
import uuid
from datetime import datetime, timezone

from app.config import Settings
from app.prompts.comic_prompt import (
    build_comic_prompt,
    count_tokens,
    MAX_PROMPT_TOKENS,
    _truncate_prompt_to_tokens,
)
from app.prompts.condense_prompt import CONDENSE_SYSTEM_PROMPT
from app.services.image_gen_client import ImageGenClient
from app.services.llm_client import LLMClient
from app.storage.file_storage import FileStorage
from app.tracing.decorators import image_gen_node

logger = logging.getLogger(__name__)

COMIC_SIZE = "2688*1536"
MAX_CONDENSE_RETRIES = 2


async def _try_condense_script(script_data: dict, settings: Settings) -> dict | None:
    """Try to condense script via LLM. Returns condensed dict or None on any failure."""
    try:
        llm = LLMClient(settings)
        script_json = json.dumps(script_data, ensure_ascii=False)
        content = await llm.chat(
            system_prompt=CONDENSE_SYSTEM_PROMPT,
            user_text=script_json,
            temperature=0.3,
        )
        condensed = LLMClient.extract_json_from_content(content)

        # Validate panel_count consistency
        if condensed.get("panel_count") != script_data["panel_count"]:
            logger.warning(
                "Condensed panel_count mismatch: got %d, expected %d",
                condensed.get("panel_count"), script_data["panel_count"],
            )
            return None

        # Validate panels array length
        if len(condensed.get("panels", [])) != script_data["panel_count"]:
            logger.warning(
                "Condensed panels length mismatch: got %d, expected %d",
                len(condensed.get("panels", [])), script_data["panel_count"],
            )
            return None

        return condensed

    except Exception as exc:
        logger.warning("LLM condense failed, falling back to truncation: %s", exc)
        return None


@image_gen_node("generate_comic")
async def generate_comic(script_data: dict, settings: Settings) -> dict:
    """Generate a comic strip image from script data.

    Flow:
      1. Build visual prompt from script_data
      2. Count tokens — if within MAX_PROMPT_TOKENS, proceed
      3. If over limit: retry up to MAX_CONDENSE_RETRIES times via LLM condense
      4. If still over after retries: force-truncate the prompt
      5. Generate image via Qwen Image 2.0
      6. Save to disk and history
    """
    # Stage 1: Build visual prompt
    prompt = build_comic_prompt(
        slang=script_data["slang"],
        origin=script_data["origin"],
        explanation=script_data["explanation"],
        panels=script_data["panels"],
    )

    logger.info(
        "漫画生成中: slang='%s' (prompt=%d 字符, %d tokens)",
        script_data["slang"], len(prompt), count_tokens(prompt),
    )

    # Stage 2: Token detection + condense retry loop
    current_data = script_data
    current_prompt = prompt

    if count_tokens(current_prompt) > MAX_PROMPT_TOKENS:
        logger.warning(
            "Prompt 超出 token 限制 (%d > %d), 开始精简重试",
            count_tokens(current_prompt), MAX_PROMPT_TOKENS,
        )

        for attempt in range(1, MAX_CONDENSE_RETRIES + 1):
            logger.info("Condense attempt %d/%d", attempt, MAX_CONDENSE_RETRIES)
            condensed = await _try_condense_script(current_data, settings)

            if condensed is not None:
                current_data = condensed
                current_prompt = build_comic_prompt(
                    slang=condensed["slang"],
                    origin=condensed["origin"],
                    explanation=condensed["explanation"],
                    panels=condensed["panels"],
                )
                token_count = count_tokens(current_prompt)
                logger.info("Condense attempt %d: prompt=%d tokens", attempt, token_count)

                if token_count <= MAX_PROMPT_TOKENS:
                    logger.info("Prompt condensed successfully within token limit")
                    break
            # else: condensed is None (LLM failed), loop continues or exits

        # Final check: still over limit after all retries?
        if count_tokens(current_prompt) > MAX_PROMPT_TOKENS:
            logger.warning(
                "Prompt 仍超出 token 限制 (%d > %d), 强制截断",
                count_tokens(current_prompt), MAX_PROMPT_TOKENS,
            )
            current_prompt = _truncate_prompt_to_tokens(current_prompt, MAX_PROMPT_TOKENS)

    # Stage 3: Generate image via Qwen Image 2.0 (text-to-image)
    img_client = ImageGenClient(settings)
    image_base64 = await img_client.generate_from_text(prompt=current_prompt, size=COMIC_SIZE)

    # Stage 4: Save to disk
    history_id = uuid.uuid4().hex
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    storage = FileStorage(settings.comic_storage_dir)
    urls = storage.save_comic(image_base64, history_id, date_str)

    logger.info("漫画已保存: history_id=%s, url=%s", history_id, urls["comic_url"])

    # Save to history
    from app.services.history_service import HistoryService
    history_svc = HistoryService(settings.history_file, settings.max_history_records)
    history_svc.add({
        "id": history_id,
        "slang": current_data["slang"],
        "origin": current_data["origin"],
        "explanation": current_data["explanation"],
        "panel_count": current_data["panel_count"],
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "comic_prompt": current_prompt,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "comic_url": urls["comic_url"],
        "thumbnail_url": urls["thumbnail_url"],
        "history_id": history_id,
    }
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest tests/backend/unit/test_comic_service.py -v`

Expected: PASS — 全部测试通过，包括原有的 `TestGenerateComic`（4 个测试）和新增的 `TestTokenCondenseRetry`（4 个测试）。

Run: `uv run pytest tests/backend/unit/ -v`

Expected: ALL PASS — 所有后端单元测试通过。

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/comic_service.py backend/app/prompts/comic_prompt.py tests/backend/unit/test_comic_service.py
git commit -m "feat(comic): add token detection + LLM condense retry in comic_service

- Add count_tokens check after build_comic_prompt
- Retry up to MAX_CONDENSE_RETRIES (2) via LLM condense
- Validate panel_count consistency after condense
- Graceful fallback: LLM failure -> force truncation
- Exhausted retries -> _truncate_prompt_to_tokens as last resort"
```
