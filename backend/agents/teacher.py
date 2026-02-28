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

    # RL bandit picks strategy, falls back to deterministic in mock mode
    def select_strategy(self, learner: LearnerState, concept_id: str, misconceptions: list[str] | None = None) -> str:
        from backend.services.llm_client import llm_client
        if llm_client.use_mock:
            return self._deterministic_strategy(learner, concept_id, misconceptions)

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

    # fallback for mock/test mode
    def _deterministic_strategy(self, learner: LearnerState, concept_id: str, misconceptions: list[str] | None = None) -> str:
        if misconceptions:
            return "debugging_exercise"

        state = learner.concept_states.get(concept_id)
        if state and state.teaching_strategies_tried:
            tried = list(state.teaching_strategies_tried.keys())
            untried = [s for s in ALL_STRATEGIES if s not in tried]
            if untried:
                return untried[0]
            return max(state.teaching_strategies_tried.items(), key=lambda x: x[1])[0]

        if learner.learning_profile.preferred_strategy:
            return learner.learning_profile.preferred_strategy

        return "socratic"

    # LLM-driven strategy selection with reflection
    async def select_strategy_smart(self, learner: LearnerState, concept_id: str,
                                    misconceptions: list[str] | None = None,
                                    session_id: str = "") -> str:
        from backend.services.llm_client import llm_client
        if llm_client.use_mock:
            return self._deterministic_strategy(learner, concept_id, misconceptions)

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

    async def teach(
        self, concept: Concept, learner: LearnerState, strategy: str | None = None, misconceptions: list[str] | None = None
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
            "socratic": "Ask probing questions that lead the learner to discover the concept. Never give the answer directly.",
            "worked_examples": "Show 2-3 worked examples of increasing complexity. Explain each step clearly.",
            "analogy": "Connect the concept to something the learner already knows. Use analogies from everyday life or mastered concepts.",
            "debugging_exercise": "Present code that contains a bug related to the concept. Ask the learner to find and fix it.",
            "explain_back": "Ask the learner to explain the concept as if teaching someone else. Gaps become visible through their explanation.",
        }

        system = f"You are an expert teacher using the {strategy} method."
        prompt = f"""CONCEPT TO TEACH: {concept.name}
DESCRIPTION: {concept.description}
DOMAIN: {concept.domain}

LEARNER PROFILE:
- Previously mastered: {mastered_names[:10]}
- Calibration trend: {learner.learning_profile.calibration_trend}
{misconception_text}

STRATEGY: {strategy}
{strategy_instructions.get(strategy, '')}

Teach the concept. End with a check-for-understanding question.

Return JSON with: teaching_content, check_question, expected_check_answer, concepts_referenced, strategy_used, estimated_time_minutes"""

        result = await self._llm_call(system, prompt)
        result["strategy_used"] = strategy
        result["concept_id"] = concept.id
        return result


teacher_agent = TeacherAgent()
