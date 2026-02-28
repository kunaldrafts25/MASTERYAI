# diagnostic agent - pre-assessment for experienced learners
# binary searches the prereq graph to figure out what they already know

import logging
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.services.knowledge_graph import knowledge_graph
from backend.config import settings

logger = logging.getLogger(__name__)


class DiagnosticAgent(BaseAgent):
    name = "diagnostic"

    def should_run_diagnostic(self, learner) -> bool:
        # skip beginners, only run if less than 60% concepts are mapped
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
        # binary search on difficulty-sorted concepts to find the knowledge boundary
        if domain:
            concepts = knowledge_graph.get_domain_concepts(domain)
        else:
            concepts = knowledge_graph.get_all_concepts()

        if not concepts:
            return []

        # sort by difficulty tier
        sorted_concepts = sorted(concepts, key=lambda c: c.difficulty_tier)

        # filter out already-mapped concepts
        unmapped = [c for c in sorted_concepts if c.id not in learner.concept_states]
        if not unmapped:
            return []

        # binary search: pick concepts at strategic positions
        probes = []
        n = len(unmapped)

        # start at the middle
        indices = [n // 2]
        # then quarter points
        if n > 4:
            indices.extend([n // 4, 3 * n // 4])
        # then fill in gaps
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
        # correct -> harder, wrong -> easier
        if not probes_remaining:
            return None

        if not results:
            # first probe: pick the middle one
            return probes_remaining[len(probes_remaining) // 2]

        last = results[-1]
        last_score = last.get("score", 0.5)

        # sort remaining by difficulty
        remaining_with_diff = []
        for cid in probes_remaining:
            concept = knowledge_graph.get_concept(cid)
            diff = concept.difficulty_tier if concept else 2
            remaining_with_diff.append((cid, diff))
        remaining_with_diff.sort(key=lambda x: x[1])

        if last_score >= 0.7:
            # correct → pick harder (from the top)
            return remaining_with_diff[-1][0]
        else:
            # wrong → pick easier (from the bottom)
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
        # returns {concept_id: inferred_status}
        from backend.agents.rl_engine import get_rl_engine
        engine = get_rl_engine(learner)

        inferred = {}

        for result in results:
            cid = result.get("concept_id", "")
            score = result.get("score", 0.0)
            mastery_threshold = engine.select_mastery_threshold(learner, cid)
            partial_threshold = mastery_threshold * 0.57  # proportional partial threshold

            if score >= mastery_threshold:
                inferred[cid] = "mastered"
                # infer all prerequisites as mastered too
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
        from backend.models.learner import ConceptMastery
        from datetime import datetime

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
            source_agent="diagnostic",
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


diagnostic_agent = DiagnosticAgent()
