from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid

MAX_SESSION_EVENTS = 200
MAX_CONVERSATION_HISTORY = 50


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentEvent(BaseModel):
    event_id: str = Field(default_factory=_uuid)
    event_type: str
    source_agent: str
    timestamp: datetime = Field(default_factory=_utcnow)
    learner_id: str = ""
    session_id: str = ""
    payload: dict = {}
    reasoning: str = ""


class Session(BaseModel):
    session_id: str = Field(default_factory=_uuid)
    learner_id: str
    started_at: datetime = Field(default_factory=_utcnow)
    ended_at: datetime | None = None
    events: list[AgentEvent] = []
    concepts_covered: list[str] = []
    concepts_mastered: list[str] = []
    misconceptions_detected: list[str] = []
    misconceptions_resolved: list[str] = []
    total_transfer_tests: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    title: str = ""
    current_concept: str | None = None
    current_state: str = "idle"  # idle | teaching | practicing | self_assessing | testing | evaluating | reteaching
    current_strategy: str | None = None
    last_teaching_content: dict | None = None
    last_test: dict | None = None
    last_evaluation: dict | None = None
    self_assessment: float | None = None
    reasoning_history: list[str] = []
    agent_messages: list[dict] = []
    engagement_state: str = "neutral"  # neutral | frustrated | bored | flow | disengaged | confused | excited
    engagement_signals: dict = {}
    conversation_history: list[dict] = []  # [{role, content, timestamp}] for emotional analysis
    engagement_analysis: dict | None = None  # Latest emotional analysis result from Tier 2
    preferred_language: str | None = None  # e.g. "cpp", "python", "java", "javascript"
    diagnostic_data: dict | None = None
    diagnostic_index: int = 0
    diagnostic_results: list[dict] = []

    def add_event(self, event: AgentEvent):
        self.events.append(event)
        if len(self.events) > MAX_SESSION_EVENTS:
            self.events = self.events[-MAX_SESSION_EVENTS:]

    def add_conversation_turn(self, role: str, content: str):
        self.conversation_history.append({
            "role": role, "content": content,
            "timestamp": _utcnow().isoformat(),
        })
        if len(self.conversation_history) > MAX_CONVERSATION_HISTORY:
            self.conversation_history = self.conversation_history[-MAX_CONVERSATION_HISTORY:]
