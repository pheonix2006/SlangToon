"""Trace collector -- execute graph and collect per-node I/O for local storage."""

import logging
import uuid
from datetime import UTC, datetime

from app.graphs.trace_models import TraceRecord, NodeRecord
from app.graphs.trace_store import TraceStore

logger = logging.getLogger(__name__)


class GraphExecutionError(Exception):
    """Wraps graph execution errors with trace_id context."""

    def __init__(self, original_error: Exception, trace_id: str | None = None):
        self.original_error = original_error
        self.trace_id = trace_id
        super().__init__(str(original_error))


def _sanitize(output: dict) -> dict:
    """Sanitize large fields in output (e.g. base64 images)."""
    if not output:
        return output
    sanitized = {}
    for k, v in output.items():
        if isinstance(v, str) and len(v) > 500:
            sanitized[k] = f"<{len(v)} chars>"
        else:
            sanitized[k] = v
    return sanitized


async def invoke_with_trace(
    graph,
    inputs: dict,
    settings,
    flow_type: str = "",
    request_id: str = "",
) -> tuple[dict, str | None]:
    """Execute graph and collect per-node I/O via astream updates.

    Returns: (final_state_dict, trace_id)
    Raises: GraphExecutionError on failure (wraps original error with trace_id).
    """
    trace_id = f"t-{uuid.uuid4().hex[:12]}" if settings.trace_enabled else None
    records = []
    config = {"configurable": {"settings": settings}}

    final_state = dict(inputs)
    try:
        async for chunk in graph.astream(
            inputs,
            config=config,
            stream_mode="updates",
        ):
            for node_name, output in chunk.items():
                records.append(
                    NodeRecord(
                        name=node_name,
                        output=_sanitize(output) if output else None,
                        timestamp=datetime.now(UTC).isoformat(),
                    )
                )
                if output:
                    final_state.update(output)

        status = "success"
    except Exception as exc:
        status = "failed"
        logger.error("Graph execution failed: %s", exc)
        raise GraphExecutionError(exc, trace_id) from exc
    finally:
        if settings.trace_enabled and trace_id:
            try:
                store = TraceStore(settings.trace_dir, settings.trace_retention_days)
                store.save(
                    TraceRecord(
                        trace_id=trace_id,
                        flow_type=flow_type,
                        request_id=request_id,
                        nodes=records,
                        status=status,
                        created_at=datetime.now(UTC).isoformat(),
                    )
                )
            except Exception:
                logger.warning("Failed to save trace", exc_info=True)

    return final_state, trace_id
