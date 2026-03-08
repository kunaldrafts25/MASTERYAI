import json
import logging
import random
from datetime import datetime
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.models.concept import Concept
from backend.models.learner import LearnerState, ConceptMastery
from backend.services.knowledge_graph import knowledge_graph
from backend.config import settings

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

        system = "You are a thoughtful tutor designing a creative challenge to see if the learner truly gets this concept — not just memorized it. Frame it as an interesting problem, not a cold exam question."
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

        # self-validation — regenerate if test quality is poor
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
        system = "You are a supportive tutor evaluating a learner's response. Be honest but kind — highlight what they got right before addressing gaps. Frame feedback as growth opportunities, not failures."
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

Evaluate their response. Score each rubric criterion (0-10), check for misconception patterns, and assess understanding level.
In your reasoning, start with what they did well, then gently address any gaps.

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

        system = "You are a friendly programming tutor creating bite-sized practice challenges. Make them feel like fun puzzles, not homework. Keep the tone encouraging."
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


    # ------------------------------------------------------------------
    # Diagnostic assessment (merged from diagnostic agent)
    # ------------------------------------------------------------------

    def should_run_diagnostic(self, learner) -> bool:
        if learner.experience_level == "beginner":
            return False

        all_concepts = knowledge_graph.get_all_concepts()
        if not all_concepts:
            return False

        mapped = len(learner.concept_states)
        total = len(all_concepts)
        if total == 0:
            return False

        mapping_ratio = mapped / total
        return mapping_ratio < 0.6

    def select_probe_concepts(self, learner, domain: str | None = None) -> list[str]:
        if domain:
            concepts = knowledge_graph.get_domain_concepts(domain)
        else:
            concepts = knowledge_graph.get_all_concepts()

        if not concepts:
            return []

        sorted_concepts = sorted(concepts, key=lambda c: c.difficulty_tier)
        unmapped = [c for c in sorted_concepts if c.id not in learner.concept_states]
        if not unmapped:
            return []

        probes = []
        n = len(unmapped)
        indices = [n // 2]
        if n > 4:
            indices.extend([n // 4, 3 * n // 4])
        if n > 8:
            indices.extend([n // 8, 3 * n // 8, 5 * n // 8, 7 * n // 8])

        seen = set()
        for idx in indices:
            idx = min(idx, n - 1)
            if idx not in seen:
                probes.append(unmapped[idx].id)
                seen.add(idx)

        return probes[:settings.max_diagnostic_probes]

    def adaptive_next_probe(self, probes_remaining: list[str],
                            results: list[dict], learner) -> str | None:
        if not probes_remaining:
            return None

        if not results:
            return probes_remaining[len(probes_remaining) // 2]

        last = results[-1]
        last_score = last.get("score", 0.5)

        remaining_with_diff = []
        for cid in probes_remaining:
            concept = knowledge_graph.get_concept(cid)
            diff = concept.difficulty_tier if concept else 2
            remaining_with_diff.append((cid, diff))
        remaining_with_diff.sort(key=lambda x: x[1])

        if last_score >= 0.7:
            return remaining_with_diff[-1][0]
        else:
            return remaining_with_diff[0][0]

    async def generate_diagnostic_question(self, concept, learner) -> dict:
        system = "You are a diagnostic assessment specialist. Generate a quick, targeted question to test if a learner already understands a concept."
        prompt = f"""CONCEPT: {concept.name}
DESCRIPTION: {concept.description}
DIFFICULTY: {concept.difficulty_tier}
LEARNER EXPERIENCE: {learner.experience_level}

Generate a single diagnostic question that can reveal whether the learner already understands this concept.
The question should be answerable in 2-3 sentences.

Return JSON: {{"question": "the diagnostic question", "key_indicators": ["what correct answer should include"], "concept_id": "{concept.id}"}}"""

        return await self._llm_call(system, prompt)

    async def evaluate_diagnostic_answer(self, concept, question_data: dict,
                                         answer: str) -> dict:
        system = "You are evaluating a diagnostic assessment answer. Be efficient — score quickly."
        prompt = f"""CONCEPT: {concept.name}
QUESTION: {question_data.get('question', '')}
KEY INDICATORS: {question_data.get('key_indicators', [])}
LEARNER'S ANSWER: {answer}

Score this answer from 0.0 to 1.0. Does the learner demonstrate understanding?

Return JSON: {{"score": 0.0-1.0, "understanding": "none|partial|solid", "notes": "brief assessment"}}"""

        return await self._llm_call(system, prompt)

    def infer_mastery_from_diagnostics(self, results: list[dict], learner) -> dict:
        from backend.agents.rl_engine import get_rl_engine
        engine = get_rl_engine(learner)

        inferred = {}
        for result in results:
            cid = result.get("concept_id", "")
            score = result.get("score", 0.0)
            mastery_threshold = engine.select_mastery_threshold(learner, cid)
            partial_threshold = mastery_threshold * 0.57

            if score >= mastery_threshold:
                inferred[cid] = "mastered"
                prereqs = knowledge_graph.get_prerequisites(cid)
                for prereq in prereqs:
                    if prereq not in inferred:
                        inferred[prereq] = "mastered"
            elif score >= partial_threshold:
                inferred[cid] = "introduced"
            else:
                inferred[cid] = "unknown"

        return inferred

    def apply_diagnostic_results(self, learner, inferred: dict):
        applied = 0
        for cid, status in inferred.items():
            if cid not in learner.concept_states:
                learner.concept_states[cid] = ConceptMastery(concept_id=cid)

            cs = learner.concept_states[cid]
            if status == "mastered" and cs.status != "mastered":
                cs.status = "mastered"
                cs.mastery_score = settings.diagnostic_inferred_score
                cs.mastered_at = datetime.utcnow()
                cs.last_validated = datetime.utcnow()
                applied += 1
            elif status == "introduced" and cs.status == "unknown":
                cs.status = "introduced"
                applied += 1

        logger.info(f"diagnostic applied {applied} status changes for learner {learner.learner_id}")
        return applied

    def post_diagnostic_results(self, learner, inferred: dict, session_id: str):
        mastered = [cid for cid, s in inferred.items() if s == "mastered"]
        introduced = [cid for cid, s in inferred.items() if s == "introduced"]

        message_bus.post(AgentMessage(
            source_agent="examiner",
            target_agent="orchestrator",
            message_type="observation",
            content=f"Diagnostic complete: {len(mastered)} concepts inferred mastered, {len(introduced)} introduced.",
            metadata={
                "mastered": mastered,
                "introduced": introduced,
                "total_probed": len(inferred),
            },
            session_id=session_id,
        ))


examiner_agent = ExaminerAgent()
