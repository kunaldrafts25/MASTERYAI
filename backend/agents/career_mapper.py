import logging
from backend.agents.base import BaseAgent
from backend.models.learner import LearnerState
from backend.models.career import CareerReadiness
from backend.services.career_service import career_service

logger = logging.getLogger(__name__)


class CareerMapperAgent(BaseAgent):
    name = "career_mapper"

    def calculate_all_readiness(self, learner: LearnerState) -> list[CareerReadiness]:
        results = []
        concept_states = {}
        for cid, cs in learner.concept_states.items():
            concept_states[cid] = {
                "status": cs.status,
                "mastery_score": cs.mastery_score,
            }

        for role_id in learner.career_targets:
            role = career_service.get_role(role_id)
            if role:
                readiness = career_service.calculate_readiness(role, concept_states)
                results.append(readiness)

        return results

    def calculate_readiness(self, learner: LearnerState, role_id: str) -> CareerReadiness | None:
        role = career_service.get_role(role_id)
        if not role:
            return None

        concept_states = {}
        for cid, cs in learner.concept_states.items():
            concept_states[cid] = {
                "status": cs.status,
                "mastery_score": cs.mastery_score,
            }

        return career_service.calculate_readiness(role, concept_states)

    def get_career_impact(self, learner: LearnerState, concept_id: str) -> dict:
        impacts = {}
        for role_id in learner.career_targets:
            current = self.calculate_readiness(learner, role_id)
            if not current:
                continue

            hypothetical_states = dict(learner.concept_states)
            from backend.models.learner import ConceptMastery
            hypothetical_states[concept_id] = ConceptMastery(
                concept_id=concept_id, status="mastered", mastery_score=0.8
            )

            concept_dict = {}
            for cid, cs in hypothetical_states.items():
                concept_dict[cid] = {"status": cs.status, "mastery_score": cs.mastery_score}

            role = career_service.get_role(role_id)
            if role:
                future = career_service.calculate_readiness(role, concept_dict)
                delta = future.overall_score - current.overall_score
                impacts[role_id] = {
                    "role_title": role.title,
                    "current_readiness": current.overall_score,
                    "projected_readiness": future.overall_score,
                    "delta": round(delta, 3),
                    "delta_pct": f"+{delta*100:.1f}%",
                }

        return impacts


career_mapper_agent = CareerMapperAgent()
