# SSE event types and stream event model

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):

    # Connection
    ACKNOWLEDGED = "acknowledged"

    # Agent activity
    AGENT_THINKING = "agent_thinking"
    THINKING_COMPLETE = "thinking_complete"

    # Response streaming
    TEXT_CHUNK = "text_chunk"

    # Tool execution
    TOOL_START = "tool_start"
    TOOL_COMPLETE = "tool_complete"

    # Learning-specific
    PHASE_CHANGE = "phase_change"

    # Completion
    RESULT = "result"
    STREAM_COMPLETE = "stream_complete"

    # Status / errors
    STATUS = "status"
    ERROR = "error"


@dataclass
class StreamEvent:

    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.event_type.value,
            "timestamp": self.timestamp,
            **self.data,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    def to_sse(self) -> str:
        return f"data: {self.to_json()}\n\n"

    # ── Factory methods ──────────────────────────────────────────────────

    @classmethod
    def acknowledged(cls) -> "StreamEvent":
        return cls(event_type=EventType.ACKNOWLEDGED)

    @classmethod
    def agent_thinking(cls, agent: str, message: str = "") -> "StreamEvent":
        return cls(
            event_type=EventType.AGENT_THINKING,
            data={"agent": agent, "message": message},
        )

    @classmethod
    def thinking_complete(cls) -> "StreamEvent":
        return cls(event_type=EventType.THINKING_COMPLETE)

    @classmethod
    def text_chunk(cls, chunk: str, agent: str = "", final: bool = False) -> "StreamEvent":
        return cls(
            event_type=EventType.TEXT_CHUNK,
            data={"chunk": chunk, "agent": agent, "final": final},
        )

    @classmethod
    def tool_start(cls, tool_name: str, agent: str = "") -> "StreamEvent":
        return cls(
            event_type=EventType.TOOL_START,
            data={"tool_name": tool_name, "agent": agent},
        )

    @classmethod
    def tool_complete(cls, tool_name: str, summary: str = "", agent: str = "") -> "StreamEvent":
        return cls(
            event_type=EventType.TOOL_COMPLETE,
            data={
                "tool_name": tool_name,
                "summary": summary[:500] if summary else "",
                "agent": agent,
            },
        )

    @classmethod
    def phase_change(cls, phase: str, concept: str = "") -> "StreamEvent":
        return cls(
            event_type=EventType.PHASE_CHANGE,
            data={"phase": phase, "concept": concept},
        )

    @classmethod
    def result(cls, data: Dict[str, Any]) -> "StreamEvent":
        return cls(event_type=EventType.RESULT, data={"result": data})

    @classmethod
    def stream_complete(cls) -> "StreamEvent":
        return cls(event_type=EventType.STREAM_COMPLETE)

    @classmethod
    def error(cls, message: str, code: Optional[str] = None) -> "StreamEvent":
        return cls(
            event_type=EventType.ERROR,
            data={"message": message, "code": code},
        )
