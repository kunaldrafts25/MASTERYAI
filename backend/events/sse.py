# SSE streaming utilities

import asyncio
import logging
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from .bus import EventBus
from .types import StreamEvent

logger = logging.getLogger(__name__)

SSE_RETRY_MS = 3000


async def sse_keepalive_generator(
    event_bus: EventBus,
    keepalive_interval: float = 30.0,
) -> AsyncGenerator[str, None]:
    # Tell the browser to auto-reconnect after SSE_RETRY_MS if disconnected
    yield f"retry: {SSE_RETRY_MS}\n\n"

    event_id = 0
    try:
        while not event_bus.is_closed:
            try:
                event = await asyncio.wait_for(
                    event_bus._queue.get(),
                    timeout=keepalive_interval,
                )
                event_id += 1
                yield event.to_sse(event_id=event_id)

                if event.event_type.value == "stream_complete":
                    break

            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

        # Drain remaining events after bus closes (race condition: bus closed
        # between timeout and while-check, leaving events undelivered)
        while not event_bus._queue.empty():
            try:
                event = event_bus._queue.get_nowait()
                event_id += 1
                yield event.to_sse(event_id=event_id)
            except asyncio.QueueEmpty:
                break

    except asyncio.CancelledError:
        logger.info("SSE keepalive generator cancelled")
        raise


def create_sse_response(event_bus: EventBus) -> StreamingResponse:
    return StreamingResponse(
        sse_keepalive_generator(event_bus),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
