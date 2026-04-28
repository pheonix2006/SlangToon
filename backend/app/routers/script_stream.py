"""POST /api/generate-script-stream -- SSE streaming script generation."""

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import Settings
from app.dependencies import get_cached_settings
from app.schemas.common import ErrorCode
from app.schemas.script import ScriptRequest
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError, LLMResponseError
from app.services.script_service import build_script_context, validate_and_finalize
from app.prompts.theme_packs import get_random_theme
from app.graphs.trace_models import TraceRecord, NodeRecord
from app.graphs.trace_store import TraceStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["script-stream"])

_USER_TEXT = "Generate a random classical idiom and its modern comic script. JSON only."


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate-script-stream")
async def generate_script_stream_endpoint(
    request: ScriptRequest = ScriptRequest(),
    settings: Settings = Depends(get_cached_settings),
) -> StreamingResponse:
    """SSE 流式 script 生成，实时推送 thinking/script/done/error 事件。"""

    async def event_generator():
        trace_id = f"t-{uuid.uuid4().hex[:12]}" if settings.trace_enabled else None
        start_time = datetime.now(UTC)
        reasoning_text = ""
        content_text = ""
        status = "success"

        try:
            theme = get_random_theme()
            system_prompt, blacklist = build_script_context(
                settings, world_setting=theme["world_setting"]
            )
            yield _sse_event("theme", {
                "theme_id": theme["id"],
                "theme_name_zh": theme["name_zh"],
            })
            llm = LLMClient(settings)

            image_base64 = request.captured_image or None

            async for chunk in llm.chat_stream(
                system_prompt=system_prompt,
                user_text=_USER_TEXT,
                temperature=0.9,
                image_base64=image_base64,
            ):
                if chunk.type == "thinking":
                    yield _sse_event("thinking", {"text": chunk.text})
                elif chunk.type == "content":
                    pass
                elif chunk.type == "done":
                    reasoning_text = chunk.reasoning
                    content_text = chunk.content

                    try:
                        data = validate_and_finalize(content_text, blacklist)
                        yield _sse_event("script", data)
                        yield _sse_event("done", {"trace_id": trace_id})
                    except (ValueError, LLMResponseError) as exc:
                        status = "failed"
                        yield _sse_event("error", {
                            "code": ErrorCode.SCRIPT_LLM_INVALID,
                            "message": str(exc),
                        })
                elif chunk.type == "error":
                    status = "failed"
                    yield _sse_event("error", {
                        "code": ErrorCode.SCRIPT_LLM_FAILED,
                        "message": chunk.text,
                    })

        except LLMTimeoutError:
            status = "failed"
            yield _sse_event("error", {
                "code": ErrorCode.SCRIPT_LLM_FAILED,
                "message": "LLM request timeout",
            })
        except LLMApiError:
            status = "failed"
            yield _sse_event("error", {
                "code": ErrorCode.SCRIPT_LLM_FAILED,
                "message": "LLM API error",
            })
        except Exception as exc:
            status = "failed"
            logger.error("Stream error: %s", exc)
            yield _sse_event("error", {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Internal error",
            })
        finally:
            if settings.trace_enabled and trace_id:
                try:
                    duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
                    store = TraceStore(settings.trace_dir, settings.trace_retention_days)
                    store.save(TraceRecord(
                        trace_id=trace_id,
                        flow_type="script_stream",
                        nodes=[NodeRecord(
                            name="script_stream_node",
                            output={"content_length": len(content_text)},
                            reasoning_content=reasoning_text or None,
                            timestamp=start_time.isoformat(),
                            duration_ms=duration_ms,
                        )],
                        status=status,
                        created_at=start_time.isoformat(),
                    ))
                except Exception:
                    logger.warning("Failed to save stream trace", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
