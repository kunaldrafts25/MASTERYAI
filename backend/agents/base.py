import logging
import time
from datetime import datetime
from backend.models.events import AgentEvent
from backend.services.llm_client import llm_client, StreamingTextExtractor
from backend.events.types import StreamEvent

logger = logging.getLogger(__name__)


class BaseAgent:

    name: str = "base"

    def _event(self, event_type: str, learner_id: str, session_id: str, payload: dict, reasoning: str) -> AgentEvent:
        return AgentEvent(
            event_type=event_type,
            source_agent=self.name,
            learner_id=learner_id,
            session_id=session_id,
            payload=payload,
            reasoning=reasoning,
        )

    async def _llm_call(self, system: str, prompt: str) -> dict:
        start = time.monotonic()
        result = await llm_client.generate(prompt=prompt, system=system)
        elapsed = round((time.monotonic() - start) * 1000)
        logger.info(f"[{self.name}] llm_call took {elapsed}ms")
        return result

    async def _llm_call_stream(self, system: str, prompt: str, event_bus=None, text_fields=None) -> dict:
        """Streaming LLM call that emits text chunks to the event bus."""
        extractor = StreamingTextExtractor(fields=text_fields) if event_bus else None
        start = time.monotonic()

        async def on_chunk(text: str):
            if extractor and event_bus:
                extracted = extractor.feed(text)
                if extracted:
                    await event_bus.emit(
                        StreamEvent.text_chunk(extracted, agent=self.name)
                    )

        result = await llm_client.generate_stream(prompt=prompt, system=system, on_chunk=on_chunk)

        if event_bus:
            await event_bus.emit(StreamEvent.text_chunk("", agent=self.name, final=True))

        elapsed = round((time.monotonic() - start) * 1000)
        logger.info(f"[{self.name}] streaming llm_call took {elapsed}ms")
        return result

    async def _emit(self, event_bus, event) -> None:
        """Emit a StreamEvent to the bus if one is active."""
        if event_bus is not None:
            await event_bus.emit(event)


async def streaming_llm_call(system: str, prompt: str, event_bus=None, agent_name: str = "", text_fields=None) -> dict:
    """Standalone streaming LLM call for use outside of agent classes (e.g. tool_library)."""
    if not event_bus:
        return await llm_client.generate(prompt=prompt, system=system)

    extractor = StreamingTextExtractor(fields=text_fields)

    async def on_chunk(text: str):
        extracted = extractor.feed(text)
        if extracted:
            await event_bus.emit(
                StreamEvent.text_chunk(extracted, agent=agent_name)
            )

    result = await llm_client.generate_stream(prompt=prompt, system=system, on_chunk=on_chunk)
    await event_bus.emit(StreamEvent.text_chunk("", agent=agent_name, final=True))
    return result
