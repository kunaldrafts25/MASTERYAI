# motivation agent - detects engagement states and suggests interventions

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



class MotivationAgent(BaseAgent):
    name = "motivation"

    def __init__(self):
        self._sessions: dict[str, EngagementSignals] = {}

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

        # update state
        signals.state = self.detect_state(session_id, learner=learner)

    # rule-based engagement detection
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


motivation_agent = MotivationAgent()
