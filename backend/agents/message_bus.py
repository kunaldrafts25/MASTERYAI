import logging
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_MESSAGES_PER_SESSION = 20


@dataclass
class AgentMessage:
    source_agent: str
    target_agent: str
    message_type: str  # recommendation, observation, warning
    content: str
    session_id: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MessageBus:

    def __init__(self):
        self._messages: dict[str, list[AgentMessage]] = {}

    def post(self, msg: AgentMessage):
        sid = msg.session_id
        if sid not in self._messages:
            self._messages[sid] = []
        self._messages[sid].append(msg)
        if len(self._messages[sid]) > MAX_MESSAGES_PER_SESSION:
            self._messages[sid] = self._messages[sid][-MAX_MESSAGES_PER_SESSION:]
        logger.info(f"[bus] {msg.source_agent} -> {msg.target_agent}: {msg.message_type} | {msg.content[:80]}")

    def get_messages(self, session_id: str, limit: int = 10) -> list[AgentMessage]:
        msgs = self._messages.get(session_id, [])
        return msgs[-limit:]

    def get_for(self, session_id: str, target: str, limit: int = 5) -> list[AgentMessage]:
        msgs = self._messages.get(session_id, [])
        filtered = [m for m in msgs if m.target_agent == target]
        return filtered[-limit:]

    def clear_session(self, session_id: str):
        self._messages.pop(session_id, None)

    def serialize(self, session_id: str) -> list[dict]:
        return [
            {
                "source_agent": m.source_agent,
                "target_agent": m.target_agent,
                "message_type": m.message_type,
                "content": m.content,
                "metadata": m.metadata,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in self._messages.get(session_id, [])
        ]


message_bus = MessageBus()
