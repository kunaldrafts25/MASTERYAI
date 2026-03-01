# motivation agent - two-tier emotional intelligence + engagement detection

import time
import logging
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage

logger = logging.getLogger(__name__)


class EngagementSignals:
    def __init__(self):
        self.response_times: list[float] = []  # seconds between prompt and answer
        self.answer_lengths: list[int] = []  # character count of answers
        self.scores: list[float] = []  # test scores
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.session_start: float = time.monotonic()
        self.total_interactions: int = 0
        self.last_interaction_time: float = time.monotonic()
        self.state: str = "neutral"
        self.encouragement_given: bool = False  # max 1 LLM call per session


# tier 2: LLM-powered emotional analysis (only when tier 1 signals something or message has markers)
class EmotionalIntelligence:

    FRUSTRATION_MARKERS = [
        "don't get", "don't understand", "makes no sense", "stupid",
        "give up", "confused", "lost", "hate", "impossible", "stuck",
        "what??", "!!!",
    ]
    EXCITEMENT_MARKERS = [
        "oh!", "i see", "that makes sense", "aha", "got it", "cool",
        "awesome", "finally", "clicked", "love",
    ]
    BOREDOM_MARKERS = [
        "boring", "already know", "too easy", "next", "skip",
        "whatever",
    ]

    def has_emotional_content(self, text: str) -> bool:
        if not text:
            return False
        lower = text.lower()
        all_markers = (
            self.FRUSTRATION_MARKERS +
            self.EXCITEMENT_MARKERS +
            self.BOREDOM_MARKERS
        )
        return any(marker in lower for marker in all_markers)

    # 1 LLM call — returns state, confidence, reasoning, nuances, recommended_tone
    async def analyze_emotion(self, conversation_history: list[dict],
                               signals: EngagementSignals,
                               learner_name: str) -> dict:
        from backend.services.llm_client import llm_client

        convo = "\n".join(
            f"[{m['role']}]: {m['content'][:200]}"
            for m in conversation_history[-8:]
        )

        system = """You are an expert at reading emotional states in educational conversations.
Analyze the learner's emotional state from their messages, response patterns, and performance signals.

Return JSON:
{
    "state": "frustrated|confused|bored|excited|flow|disengaged|neutral",
    "confidence": 0.0-1.0,
    "reasoning": "1-2 sentence explanation",
    "nuances": ["specific observation 1", "specific observation 2"],
    "recommended_tone": "encouraging|challenging|patient|celebratory"
}

Consider:
- Message tone and word choice matter more than test scores
- Short, terse answers may indicate frustration or disengagement
- Long, exploratory answers often indicate flow or excitement
- Repeated "I don't understand" is different from "Let me try again"
- Cultural context: some learners express frustration indirectly"""

        prompt = f"""Learner: {learner_name}
Recent conversation:
{convo}

Performance signals:
- Consecutive failures: {signals.consecutive_failures}
- Consecutive successes: {signals.consecutive_successes}
- Total interactions this session: {signals.total_interactions}
- Recent answer lengths: {signals.answer_lengths[-5:]}
- Current quantitative state: {signals.state}

What is this learner's emotional state?"""

        return await llm_client.generate(prompt, system=system)

    # 1 LLM call — generates a personalized intervention referencing specific context
    async def generate_intervention(self, emotional_state: dict,
                                      learner_name: str,
                                      concept_name: str,
                                      conversation_history: list[dict]) -> dict:
        from backend.services.llm_client import llm_client

        recent_learner_msg = ""
        for m in reversed(conversation_history):
            if m.get("role") == "learner":
                recent_learner_msg = m["content"][:200]
                break

        system = f"""Generate a brief, personalized intervention for a learner who is {emotional_state['state']}.

Rules:
- Reference something specific from their recent interaction
- Keep it to 1-2 sentences
- Be genuine, not patronizing
- Match the recommended tone: {emotional_state.get('recommended_tone', 'encouraging')}

Return JSON:
{{
    "type": "encouragement|challenge|break_suggestion|celebration",
    "message": "Your personalized message",
    "action": "reduce_difficulty|increase_difficulty|suggest_break|null"
}}"""

        prompt = f"""Learner: {learner_name}
Current topic: {concept_name}
Emotional state: {emotional_state['state']} (confidence: {emotional_state.get('confidence', 0)})
Nuances: {emotional_state.get('nuances', [])}
Last learner message: "{recent_learner_msg}" """

        result = await llm_client.generate(prompt, system=system)
        result["engagement_state"] = emotional_state["state"]
        result["personalized"] = True
        return result


class MotivationAgent(BaseAgent):
    name = "motivation"

    def __init__(self):
        self._sessions: dict[str, EngagementSignals] = {}
        self._emotional_intelligence = EmotionalIntelligence()
        self._conversation_history: dict[str, list[dict]] = {}  # session_id -> messages

    def _get_signals(self, session_id: str) -> EngagementSignals:
        if session_id not in self._sessions:
            self._sessions[session_id] = EngagementSignals()
        return self._sessions[session_id]

    def _get_engagement_profile(self, session_id: str, learner=None) -> tuple:
        from backend.agents.rl_engine import DEFAULT_ENGAGEMENT_PROFILE, get_rl_engine
        if learner is None:
            return DEFAULT_ENGAGEMENT_PROFILE
        signals = self._get_signals(session_id)
        engine = get_rl_engine(learner)
        session_minutes = (time.monotonic() - signals.session_start) / 60
        return engine.select_engagement_profile(
            session_minutes, signals.scores, signals.response_times
        )

    def record_message(self, session_id: str, role: str, content: str):
        if session_id not in self._conversation_history:
            self._conversation_history[session_id] = []
        self._conversation_history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": time.monotonic(),
        })
        # Keep last 20 messages per session
        self._conversation_history[session_id] = self._conversation_history[session_id][-20:]

    def get_conversation_history(self, session_id: str) -> list[dict]:
        return self._conversation_history.get(session_id, [])

    def record_interaction(self, session_id: str, answer_text: str,
                           score: float | None = None, is_test_result: bool = False,
                           learner=None):
        signals = self._get_signals(session_id)
        now = time.monotonic()

        # response time
        response_time = now - signals.last_interaction_time
        signals.response_times.append(response_time)
        signals.last_interaction_time = now
        signals.total_interactions += 1

        # answer length
        signals.answer_lengths.append(len(answer_text) if answer_text else 0)

        # test scores
        if is_test_result and score is not None:
            signals.scores.append(score)
            if score < 0.4:
                signals.consecutive_failures += 1
                signals.consecutive_successes = 0
            elif score >= 0.7:
                signals.consecutive_successes += 1
                signals.consecutive_failures = 0
            else:
                # partial: don't reset streaks aggressively
                signals.consecutive_failures = max(0, signals.consecutive_failures - 1)

        # update state (Tier 1)
        signals.state = self.detect_state(session_id, learner=learner)

    # tier 1: rule-based engagement detection (zero LLM calls)
    def detect_state(self, session_id: str, learner=None) -> str:
        signals = self._get_signals(session_id)
        profile = self._get_engagement_profile(session_id, learner)
        frust_failures, bored_speed, flow_range, session_max, decline_thresh, short_len = profile

        # frustrated: N+ consecutive failures OR (N-1)+ failures + short answers
        if signals.consecutive_failures >= frust_failures:
            return "frustrated"
        if signals.consecutive_failures >= max(1, frust_failures - 1) and signals.answer_lengths:
            recent_lengths = signals.answer_lengths[-3:]
            if any(length < short_len for length in recent_lengths):
                return "frustrated"

        # bored: 3+ fast correct answers
        if signals.consecutive_successes >= 3 and len(signals.response_times) >= 3:
            recent_times = signals.response_times[-3:]
            if all(t < bored_speed for t in recent_times):
                return "bored"

        # flow: 3+ correct answers in flow time range
        if signals.consecutive_successes >= 3 and len(signals.response_times) >= 3:
            recent_times = signals.response_times[-3:]
            if all(flow_range[0] <= t <= flow_range[1] for t in recent_times):
                return "flow"

        # disengaged: session > max minutes + declining quality
        session_minutes = (time.monotonic() - signals.session_start) / 60
        if session_minutes > session_max and len(signals.scores) >= 3:
            recent = signals.scores[-3:]
            earlier = signals.scores[:3]
            if sum(recent) / len(recent) < sum(earlier) / len(earlier) + decline_thresh:
                return "disengaged"

        return "neutral"

    # tier 1 (numeric) then tier 2 (LLM) if warranted
    async def detect_state_with_context(self, session_id: str,
                                         learner=None,
                                         learner_name: str = "") -> dict:
        signals = self._get_signals(session_id)

        # Tier 1: Fast numeric detection
        numeric_state = self.detect_state(session_id, learner=learner)

        # Check if Tier 2 is warranted
        conversation = self._conversation_history.get(session_id, [])
        last_message = conversation[-1]["content"] if conversation else ""

        needs_llm = (
            numeric_state != "neutral"  # Numeric signals say something is off
            or self._emotional_intelligence.has_emotional_content(last_message)  # Content has markers
        )

        if not needs_llm:
            return {"state": "neutral", "source": "numeric", "analysis": None}

        # Tier 2: LLM emotional analysis
        try:
            analysis = await self._emotional_intelligence.analyze_emotion(
                conversation, signals, learner_name
            )
            return {
                "state": analysis.get("state", numeric_state),
                "source": "llm",
                "analysis": analysis,
            }
        except Exception as e:
            logger.warning("LLM emotional analysis failed: %s — using numeric state", e)
            return {"state": numeric_state, "source": "numeric", "analysis": None}

    def get_intervention(self, session_id: str, learner) -> dict | None:
        state = self.detect_state(session_id)

        if state == "frustrated":
            return {
                "type": "encouragement",
                "message": "Learning is all about the journey. Mistakes are how we grow. Let's try a different approach — sometimes seeing it from a new angle makes everything click.",
                "action": "reduce_difficulty",
                "engagement_state": "frustrated",
            }

        if state == "bored":
            return {
                "type": "challenge",
                "message": "You're flying through this! Let's step it up with something more challenging to keep you in your growth zone.",
                "action": "increase_difficulty",
                "engagement_state": "bored",
            }

        if state == "disengaged":
            return {
                "type": "break_suggestion",
                "message": "You've been at this for a while. Research shows that taking short breaks actually improves retention. How about a 5-minute breather?",
                "action": "suggest_break",
                "engagement_state": "disengaged",
            }

        # flow — don't interrupt!
        return None

    async def get_intervention_personalized(self, session_id: str,
                                             learner, concept_name: str = "") -> dict | None:
        emotion = await self.detect_state_with_context(
            session_id, learner=learner,
            learner_name=getattr(learner, "name", "")
        )

        if emotion["state"] in ("neutral", "flow"):
            return None  # Don't interrupt flow, don't intervene on neutral

        # If LLM analysis available, generate personalized intervention
        if emotion["analysis"]:
            conversation = self._conversation_history.get(session_id, [])
            return await self._emotional_intelligence.generate_intervention(
                emotion["analysis"],
                getattr(learner, "name", ""),
                concept_name,
                conversation,
            )

        # Fall back to canned interventions for numeric-only detection
        return self.get_intervention(session_id, learner)

    def celebrate_milestone(self, learner, milestone_type: str, session_id: str):
        celebrations = {
            "concept_mastered": f"Concept mastered! {learner.learning_profile.total_concepts_mastered} concepts and counting.",
            "streak_3": "3 in a row! You're on fire.",
            "first_mastery": "Your first concept mastered! This is just the beginning.",
            "misconception_resolved": "You've overcome a misconception — that's real growth.",
        }

        msg = celebrations.get(milestone_type, f"Milestone reached: {milestone_type}")

        message_bus.post(AgentMessage(
            source_agent="motivation",
            target_agent="orchestrator",
            message_type="celebration",
            content=msg,
            metadata={"milestone": milestone_type},
            session_id=session_id,
        ))

    def post_observation(self, session_id: str, learner):
        signals = self._get_signals(session_id)
        state = signals.state

        if state == "neutral":
            return  # don't spam the bus with neutral states

        intervention = self.get_intervention(session_id, learner)
        content = f"Engagement state: {state}."
        if intervention:
            content += f" Recommended: {intervention['action']}."

        message_bus.post(AgentMessage(
            source_agent="motivation",
            target_agent="orchestrator",
            message_type="warning" if state in ("frustrated", "disengaged") else "observation",
            content=content,
            metadata={
                "engagement_state": state,
                "intervention": intervention,
                "signals_summary": {
                    "consecutive_failures": signals.consecutive_failures,
                    "consecutive_successes": signals.consecutive_successes,
                    "total_interactions": signals.total_interactions,
                },
            },
            session_id=session_id,
        ))

    def cleanup_session(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._conversation_history.pop(session_id, None)


motivation_agent = MotivationAgent()
