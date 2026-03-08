import json
import logging
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.agents.rl_engine import get_rl_engine, ALL_STRATEGIES
from backend.models.concept import Concept
from backend.models.learner import LearnerState

logger = logging.getLogger(__name__)


class TeacherAgent(BaseAgent):
    name = "teacher"

    def select_strategy(self, learner: LearnerState, concept_id: str, misconceptions: list[str] | None = None) -> str:
        engine = get_rl_engine(learner)
        # adaptive exclusion: exclude strategies statistically underperforming
        exclude = engine.strategy_bandit.get_exclusion_set()
        # also exclude strategies that scored poorly for this specific concept
        cs = learner.concept_states.get(concept_id)
        if cs:
            for strat, score in cs.teaching_strategies_tried.items():
                if score < 0.3 and strat not in exclude:
                    exclude.append(strat)
        selected = engine.select_strategy(exclude=exclude or None)
        logger.info(f"RL bandit selected strategy: {selected} (excluded: {exclude})")
        return selected

    async def select_strategy_smart(self, learner: LearnerState, concept_id: str,
                                    misconceptions: list[str] | None = None,
                                    session_id: str = "") -> str:
        cs = learner.concept_states.get(concept_id)
        if not cs or not cs.teaching_strategies_tried:
            return self.select_strategy(learner, concept_id, misconceptions)

        reflection = await self.reflect(learner, concept_id, misconceptions or [], session_id)
        recommended = reflection.get("recommended_strategy", "")
        if recommended in ALL_STRATEGIES:
            return recommended

        return self.select_strategy(learner, concept_id, misconceptions)

    async def reflect(self, learner: LearnerState, concept_id: str,
                      misconceptions: list[str], session_id: str = "") -> dict:
        cs = learner.concept_states.get(concept_id)
        strategy_history = cs.teaching_strategies_tried if cs else {}
        last_score = list(strategy_history.values())[-1] if strategy_history else 0.0
        last_strategy = list(strategy_history.keys())[-1] if strategy_history else "unknown"

        system = "You are a reflective teaching agent analyzing learning outcomes to improve your approach."
        prompt = f"""CONCEPT: {concept_id}
LAST STRATEGY USED: {last_strategy}
LAST TEST SCORE: {last_score}
MISCONCEPTIONS DETECTED: {misconceptions}

ALL STRATEGY HISTORY FOR THIS CONCEPT:
{json.dumps(strategy_history)}

AVAILABLE STRATEGIES: {ALL_STRATEGIES}

LEARNER PROFILE:
- Calibration trend: {learner.learning_profile.calibration_trend}
- Experience: {learner.experience_level}
- Strengths: {learner.learning_profile.strengths}
- Weaknesses: {learner.learning_profile.weaknesses}

Reflect on what happened. Why did the last strategy score {last_score}?
What patterns do you see? Which strategy should we try next and why?

Return JSON: {{"reflection": "your analysis of what happened", "recommended_strategy": "one of the available strategies", "reasoning": "why this strategy will work better", "confidence": 0.0-1.0}}"""

        result = await self._llm_call(system, prompt)

        message_bus.post(AgentMessage(
            source_agent="teacher",
            target_agent="orchestrator",
            message_type="recommendation",
            content=f"Reflection: {result.get('reflection', '')[:100]}. Recommending: {result.get('recommended_strategy', '?')}",
            metadata=result,
            session_id=session_id,
        ))

        return result

    def opine(self, session, learner):
        from backend.agents.deliberation import AgentOpinion

        cid = session.current_concept
        if not cid:
            return None

        cs = learner.concept_states.get(cid)
        if cs and len(cs.teaching_strategies_tried) >= 2:
            strategy = self.select_strategy(learner, cid)
            worst = min(cs.teaching_strategies_tried.items(), key=lambda x: x[1])
            return AgentOpinion(
                agent_name="teacher",
                recommendation="switch_strategy",
                reasoning=f"Strategy '{worst[0]}' scored {worst[1]:.1f}. Recommending '{strategy}' instead.",
                confidence=0.6,
                priority="advisory",
            )
        return None

    async def teach(
        self, concept: Concept, learner: LearnerState, strategy: str | None = None,
        misconceptions: list[str] | None = None, event_bus=None
    ) -> dict:
        if not strategy:
            strategy = self.select_strategy(learner, concept.id, misconceptions)

        mastered_names = []
        for cid, cs in learner.concept_states.items():
            if cs.status == "mastered":
                mastered_names.append(cid)

        misconception_text = ""
        if misconceptions:
            for m in concept.common_misconceptions:
                if m.id in misconceptions:
                    misconception_text += f"\nActive misconception: {m.id} - {m.description}"

        strategy_instructions = {
            "socratic": "Guide them to discover the concept through thoughtful questions. Don't give the answer — help them find it.",
            "worked_examples": "Walk through 2-3 examples, building from simple to complex. Explain your thinking at each step like a mentor would.",
            "analogy": "Connect this to something they already know. Use relatable, everyday analogies or build on concepts they've mastered.",
            "debugging_exercise": "Show them code with a subtle bug related to the concept. Challenge them to spot and fix it — make it feel like a puzzle, not a test.",
            "explain_back": "Ask them to explain the concept in their own words, as if teaching a friend. This reveals gaps naturally.",
        }

        system = f"""You are a friendly, skilled tutor who makes learning feel like a great conversation.
Use the {strategy} method, but keep it natural — talk like a knowledgeable friend, not a textbook.
Be encouraging, use casual language, and make the learner feel smart for asking questions.
Break down complex ideas into digestible pieces. Use real-world examples they can relate to."""

        prompt = f"""CONCEPT TO TEACH: {concept.name}
DESCRIPTION: {concept.description}
DOMAIN: {concept.domain}

LEARNER PROFILE:
- Previously mastered: {mastered_names[:10]}
- Calibration trend: {learner.learning_profile.calibration_trend}
{misconception_text}

STRATEGY: {strategy}
{strategy_instructions.get(strategy, '')}

Teach this concept conversationally. Make it engaging and clear — like you're explaining it to a curious friend over coffee.
End with a natural check-for-understanding question (not a quiz — more like "Does that make sense? What do you think would happen if...?").

Return JSON with: teaching_content, check_question, expected_check_answer, concepts_referenced, strategy_used, estimated_time_minutes"""

        if event_bus:
            result = await self._llm_call_stream(system, prompt, event_bus=event_bus)
        else:
            result = await self._llm_call(system, prompt)
        result["strategy_used"] = strategy
        result["concept_id"] = concept.id
        return result


teacher_agent = TeacherAgent()
