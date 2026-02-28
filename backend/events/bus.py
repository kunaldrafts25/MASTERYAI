# async event bus for SSE streaming

import asyncio
import logging
from typing import AsyncIterator

from .types import EventType, StreamEvent

logger = logging.getLogger(__name__)


class EventBus:

    def __init__(self, max_queue_size: int = 1000):
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._closed = False

    async def emit(self, event: StreamEvent) -> None:
        if self._closed:
            logger.warning("Attempted to emit to closed EventBus")
            return
        try:
            await self._queue.put(event)
        except asyncio.QueueFull:
            logger.error("Event queue full, dropping event: %s", event.event_type)

    async def stream(self) -> AsyncIterator[StreamEvent]:
        while not self._closed:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=60.0)
                yield event
                if event.event_type == EventType.STREAM_COMPLETE:
                    self._closed = True
                    break
            except asyncio.TimeoutError:
                logger.debug("EventBus stream timeout, continuing")
                continue
            except asyncio.CancelledError:
                logger.info("EventBus stream cancelled")
                self._closed = True
                break

    def close(self) -> None:
        self._closed = True

    @property
    def is_closed(self) -> bool:
        return self._closed
