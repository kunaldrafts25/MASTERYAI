import json
import logging
import random
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.models.concept import Concept
from backend.models.learner import LearnerState

logger = logging.getLogger(__name__)


class ExaminerAgent(BaseAgent):
    name = "examiner"

    async def generate_transfer_test(
        self, concept: Concept, learner: LearnerState, difficulty_tier: int = 2
    ) -> dict:
        seen_contexts = []
        state = learner.concept_states.get(concept.id)
        if state:
            seen_contexts = state.contexts_encountered

        available_test_contexts = [c for c in concept.test_contexts if c not in seen_contexts]
        if not available_test_contexts:
            available_test_contexts = concept.test_contexts

        suspected = []
        if state:
            suspected = state.misconceptions_active

        misconceptions_text = "\n".join(
            f"- {m.id}: {m.description} (indicators: {', '.join(m.indicators)})"
            for m in concept.common_misconceptions
        )

        system = "You are an expert examiner validating deep understanding through transfer tests."
        prompt = f"""CONCEPT BEING TESTED: {concept.name}
CONCEPT DESCRIPTION: {concept.description}
CONCEPT DOMAIN: {concept.domain}

LEARNER CONTEXT (DO NOT reuse these):
- Teaching contexts: {concept.teaching_contexts}
- Previous test contexts: {seen_contexts}

KNOWN MISCONCEPTIONS:
{misconceptions_text}

SUSPECTED MISCONCEPTIONS FOR THIS LEARNER: {suspected}

Generate a transfer test that:
1. Presents {concept.name} in a COMPLETELY NEW context not listed above
2. Requires APPLYING the concept, not just recognizing it
3. Includes traps for common misconceptions
4. Has clear evaluation criteria

DIFFICULTY TIER: {difficulty_tier}

Return JSON with: problem_statement, context_description, response_format, correct_approach, misconception_traps, rubric, follow_up_if_correct, estimated_time_minutes"""

        result = await self._llm_call(system, prompt)
        result["concept_id"] = concept.id
        result["difficulty_tier"] = difficulty_tier

        # self-validation — only in non-mock mode
        from backend.services.llm_client import llm_client
        if not llm_client.use_mock:
            validation = await self.validate_test(result, concept)
            result["validation"] = validation

            if not validation.get("is_valid", True):
                logger.info(f"test validation failed: {validation.get('issues')}. regenerating.")
                result = await self._llm_call(
                    system,
                    prompt + f"\n\nPREVIOUS ATTEMPT HAD ISSUES: {validation.get('issues')}\nFix these issues in the new version."
                )
                result["concept_id"] = concept.id
                result["difficulty_tier"] = difficulty_tier
                result["regenerated"] = True

        return result

    async def validate_test(self, test_data: dict, concept: Concept) -> dict:
        system = "You are a test quality reviewer for an intelligent tutoring system."
        test_summary = json.dumps(test_data, default=str)[:1500]
        prompt = f"""Review this transfer test for quality:

CONCEPT: {concept.name} - {concept.description}

TEST:
{test_summary}

Evaluate:
1. Does it test TRANSFER (applying in new context), not just RECALL (restating definitions)?
2. Is it fair — does it only assume knowledge the learner should have?
3. Is the rubric clear and objectively scorable?
4. Are misconception traps well-designed and subtle?

Return JSON: {{"is_valid": true/false, "issues": ["list of problems if any"], "quality_score": 0.0-1.0, "suggestion": "how to improve if needed"}}"""

        return await self._llm_call(system, prompt)

    async def evaluate_response(
        self, concept: Concept, test_data: dict, learner_response: str
    ) -> dict:
        system = "You are evaluating a learner's response to a transfer test."
        prompt = f"""ORIGINAL PROBLEM:
{test_data.get('problem_statement', '')}

CORRECT APPROACH:
{test_data.get('correct_approach', '')}

MISCONCEPTION TRAPS:
{test_data.get('misconception_traps', [])}

RUBRIC:
{test_data.get('rubric', [])}

LEARNER'S RESPONSE:
{learner_response}

Evaluate: score each rubric criterion (0-10), check for misconception patterns, assess understanding level.

Return JSON with: rubric_scores, total_score (0.0-1.0), misconceptions_detected, understanding_level, reasoning, recommended_focus"""

        result = await self._llm_call(system, prompt)

        raw_score = result.get("total_score", 0.5)
        if isinstance(raw_score, str):
            raw_score = float(raw_score.strip().rstrip("%"))
        raw_score = float(raw_score)
        if raw_score > 1.0:
            raw_score = raw_score / 100.0
        result["total_score"] = round(max(0.0, min(1.0, raw_score)), 3)

        if not isinstance(result.get("rubric_scores"), list):
            result["rubric_scores"] = []
        if not isinstance(result.get("misconceptions_detected"), list):
            result["misconceptions_detected"] = []

        # post misconception warnings to bus
        misconceptions = result.get("misconceptions_detected", [])
        if misconceptions:
            ids = [m.get("misconception_id", str(m)) for m in misconceptions if isinstance(m, dict)]
            if ids:
                message_bus.post(AgentMessage(
                    source_agent="examiner",
                    target_agent="orchestrator",
                    message_type="warning",
                    content=f"Misconceptions detected: {ids}. Score: {result['total_score']:.2f}",
                    metadata={"misconceptions": ids, "score": result["total_score"]},
                    session_id="",
                ))

        return result

    async def generate_practice(self, concept: Concept, learner: LearnerState | None = None, count: int | None = None) -> list[dict]:
        from backend.config import settings
        if count is None:
            count = settings.default_practice_count
        context = random.choice(concept.teaching_contexts) if concept.teaching_contexts else "general programming"

        mastered_names = []
        if learner:
            mastered_names = [cid for cid, cs in learner.concept_states.items() if cs.status == "mastered"]

        system = "You are a programming tutor creating practice problems."
        prompt = f"""CONCEPT: {concept.name}
DESCRIPTION: {concept.description}
DOMAIN: {concept.domain}
TEACHING CONTEXTS: {concept.teaching_contexts}
LEARNER'S MASTERED CONCEPTS: {mastered_names[:8]}

Generate {count} practice problems for {concept.name} in the context of {context}.
These should be EASIER than transfer tests — they reinforce understanding in familiar contexts.
Each problem should be self-contained and solvable in 2-3 minutes.

Return JSON with a "problems" array, each object having:
problem_id (string), problem_statement (string with code examples if relevant), context (string), difficulty ("familiar"), hints (array of 2 strings), expected_approach (string)"""

        logger.info(f"generating {count} practice problems for {concept.id}")
        result = await self._llm_call(system, prompt)

        problems = result.get("problems", [])
        if not isinstance(problems, list) or len(problems) == 0:
            problems = [result] if "problem_statement" in result else []

        for i, p in enumerate(problems):
            p.setdefault("problem_id", f"practice_{concept.id}_{i}")
            p.setdefault("difficulty", "familiar")
            p.setdefault("hints", [])

        return problems[:count]


examiner_agent = ExaminerAgent()
