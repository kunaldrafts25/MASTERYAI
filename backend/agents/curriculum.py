import logging
from backend.agents.base import BaseAgent
from backend.agents.message_bus import message_bus, AgentMessage
from backend.models.learner import LearnerState
from backend.services.knowledge_graph import knowledge_graph
from backend.services.career_service import career_service

logger = logging.getLogger(__name__)


class CurriculumAgent(BaseAgent):
    name = "curriculum"

    def select_next_concept(self, learner: LearnerState) -> str | None:
        mastered = {
            cid for cid, cs in learner.concept_states.items()
            if cs.status == "mastered"
        }

        target_concepts = set()
        for role_id in learner.career_targets:
            target_concepts.update(career_service.get_required_concepts(role_id))

        if not target_concepts:
            # use all available domains, not just python
            for c in knowledge_graph.get_all_concepts():
                target_concepts.add(c.id)

        if not target_concepts:
            return None

        path = knowledge_graph.compute_learning_path(
            target_concepts, mastered, learner.learning_profile.domain_velocities
        )

        for step in path:
            cid = step["concept_id"]
            state = learner.concept_states.get(cid)
            if not state or state.status in ("unknown", "introduced"):
                prereqs = knowledge_graph.get_prerequisites(cid)
                prereqs_met = all(
                    learner.concept_states.get(p, None) and learner.concept_states[p].status == "mastered"
                    for p in prereqs
                )
                if prereqs_met or not prereqs:
                    return cid

        for step in path:
            return step["concept_id"]

        return None

    def generate_learning_path(self, learner: LearnerState, role_id: str | None = None) -> list[dict]:
        mastered = {
            cid for cid, cs in learner.concept_states.items()
            if cs.status == "mastered"
        }

        target_concepts = set()
        if role_id:
            target_concepts = career_service.get_required_concepts(role_id)
        else:
            for rid in learner.career_targets:
                target_concepts.update(career_service.get_required_concepts(rid))

        if not target_concepts:
            # use all available domains, not just python
            for c in knowledge_graph.get_all_concepts():
                target_concepts.add(c.id)

        path = knowledge_graph.compute_learning_path(
            target_concepts, mastered, learner.learning_profile.domain_velocities
        )

        total_hours = 0
        for step in path:
            total_hours += step["estimated_hours"]
            concept = knowledge_graph.get_concept(step["concept_id"])
            step["concept_name"] = concept.name if concept else step["concept_id"]
            step["domain"] = concept.domain if concept else "unknown"
            transfers = []
            for mid in mastered:
                edge = knowledge_graph.get_transfer_edge(mid, step["concept_id"])
                if edge:
                    transfers.append(mid)
            step["transfer_bonus_from"] = transfers

        return path

    def get_decayed_concepts(self, learner: LearnerState) -> list[str]:
        from datetime import datetime
        from backend.agents.rl_engine import get_rl_engine, DEFAULT_SM2_PROFILE
        now = datetime.utcnow()
        decayed = []

        # load adaptive SM-2 profile for decay calculation
        try:
            engine = get_rl_engine(learner)
            sm2_profile = engine.select_sm2_profile(learner)
        except Exception:
            sm2_profile = DEFAULT_SM2_PROFILE
        init_ef, min_ef, ef_coeffs, miscon_penalty, _ = sm2_profile

        for cid, cs in learner.concept_states.items():
            if cs.status != "mastered" or not cs.last_validated:
                continue

            concept = knowledge_graph.get_concept(cid)
            if not concept:
                continue

            success_count = sum(1 for t in cs.transfer_tests if t.score >= 0.7)
            base_days = concept.mastery_criteria.time_decay_days

            if success_count <= 1:
                interval = base_days * 0.5
            else:
                easiness = min(init_ef, min_ef + 0.1 * success_count)
                interval = base_days * (easiness ** (success_count - 1))

            if cs.misconceptions_resolved:
                interval *= (1.0 - miscon_penalty)

            days_since = (now - cs.last_validated).days
            if days_since > interval:
                decay_ratio = days_since / max(interval, 1)
                decayed.append((cid, decay_ratio))

        decayed.sort(key=lambda x: x[1], reverse=True)
        result = [cid for cid, _ in decayed[:3]]
        if result:
            logger.info(f"found {len(result)} decayed concepts: {result}")
        return result

    def opine(self, session, learner):
        from backend.agents.deliberation import AgentOpinion

        decayed = self.get_decayed_concepts(learner)
        if decayed:
            return AgentOpinion(
                agent_name="curriculum",
                recommendation="review",
                reasoning=f"Concept '{decayed[0]}' has decayed. Review before advancing.",
                confidence=0.6,
                priority="important",
            )

        next_concept = self.select_next_concept(learner)
        if next_concept:
            return AgentOpinion(
                agent_name="curriculum",
                recommendation="advance",
                reasoning=f"Next concept on path: '{next_concept}'. Prerequisites satisfied.",
                confidence=0.5,
                priority="advisory",
            )
        return None

    def post_recommendations(self, learner: LearnerState, session_id: str):
        decayed = self.get_decayed_concepts(learner)
        if decayed:
            message_bus.post(AgentMessage(
                source_agent="curriculum",
                target_agent="orchestrator",
                message_type="warning",
                content=f"{len(decayed)} concepts may have decayed: {decayed}. Consider retesting before new material.",
                metadata={"decayed_concepts": decayed},
                session_id=session_id,
            ))

        next_concept = self.select_next_concept(learner)
        if next_concept:
            concept = knowledge_graph.get_concept(next_concept)
            prereqs = knowledge_graph.get_prerequisites(next_concept)
            prereqs_met = all(
                learner.concept_states.get(p) and learner.concept_states[p].status == "mastered"
                for p in prereqs
            ) if prereqs else True

            msg = f"Recommended next concept: {concept.name + ' (' + next_concept + ')' if concept else next_concept}."
            if not prereqs_met:
                msg += f" Warning: prerequisites {prereqs} not all mastered."

            message_bus.post(AgentMessage(
                source_agent="curriculum",
                target_agent="orchestrator",
                message_type="recommendation",
                content=msg,
                metadata={"next_concept": next_concept, "prereqs_met": prereqs_met},
                session_id=session_id,
            ))


curriculum_agent = CurriculumAgent()
