import logging
import time
from datetime import datetime
from backend.models.events import AgentEvent
from backend.services.llm_client import llm_client

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

    async def _emit(self, event_bus, event) -> None:
        """Emit a StreamEvent to the bus if one is active."""
        if event_bus is not None:
            await event_bus.emit(event)
