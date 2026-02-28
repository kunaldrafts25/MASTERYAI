# SSE streaming utilities

import asyncio
import logging
from typing import AsyncGenerator

from starlette.responses import StreamingResponse

from .bus import EventBus
from .types import StreamEvent

logger = logging.getLogger(__name__)


async def sse_keepalive_generator(
    event_bus: EventBus,
    keepalive_interval: float = 30.0,
) -> AsyncGenerator[str, None]:
    try:
        while not event_bus.is_closed:
            try:
                event = await asyncio.wait_for(
                    event_bus._queue.get(),
                    timeout=keepalive_interval,
                )
                yield event.to_sse()

                if event.event_type.value == "stream_complete":
                    break

            except asyncio.TimeoutError:
                yield ": keepalive\n\n"

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
