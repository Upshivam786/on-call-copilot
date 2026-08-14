"""Streaming utilities for Server-Sent Events (SSE)."""

from typing import AsyncGenerator, Any

from fastapi.responses import StreamingResponse
import json


class SSEFormatter:
    """Format agent loop events as Server-Sent Events."""

    @staticmethod
    def format_event(event_type: str, data: dict[str, Any]) -> str:
        """Format a single SSE event."""
        payload = {"type": event_type, **data}
        return f"data: {json.dumps(payload, default=str)}\n\n"

    @staticmethod
    def format_error(error: str) -> str:
        """Format an error event."""
        return f"data: {json.dumps({'type': 'error', 'content': error})}\n\n"

    @staticmethod
    def format_done() -> str:
        """Format the end-of-stream event."""
        return "data: [DONE]\n\n"


async def sse_wrapper(
    agent_stream: AsyncGenerator[dict[str, Any], None],
) -> AsyncGenerator[str, None]:
    """Wrap agent stream output as SSE."""
    try:
        async for event in agent_stream:
            event_type = event.get("type", "message")
            data = {k: v for k, v in event.items() if k != "type"}
            yield SSEFormatter.format_event(event_type, data)
    except Exception as e:
        yield SSEFormatter.format_error(str(e))
    finally:
        yield SSEFormatter.format_done()


def build_sse_response(agent_stream: AsyncGenerator[dict, None]) -> StreamingResponse:
    """Build a StreamingResponse for SSE."""
    return StreamingResponse(
        sse_wrapper(agent_stream),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )