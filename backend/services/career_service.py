import json
from pathlib import Path
from backend.models.career import CareerRole, CareerReadiness, SkillGap
from backend.config import settings


class CareerService:

    def __init__(self):
        self.roles: dict[str, CareerRole] = {}

    def load(self, path: str | None = None):
        p = Path(path or settings.career_roles_path)
        with open(p) as f:
            data = json.load(f)
        for raw in data["roles"]:
            role = CareerRole(**raw)
            self.roles[role.id] = role

    def get_role(self, role_id: str) -> CareerRole | None:
        return self.roles.get(role_id)

    def get_all_roles(self) -> list[CareerRole]:
        return list(self.roles.values())

    def calculate_readiness(self, role: CareerRole, concept_states: dict) -> CareerReadiness:
        skill_breakdown = []
        gaps = []
        total_weighted = 0.0
        total_weight = 0.0

        for skill in role.required_skills:
            scores = []
            mastered_count = 0
            for cid in skill.concept_ids:
                state = concept_states.get(cid)
                if state and state.get("status") == "mastered":
                    scores.append(state.get("mastery_score", 0.0))
                    mastered_count += 1
                else:
                    score = state.get("mastery_score", 0.0) if state else 0.0
                    scores.append(score)

            avg_score = sum(scores) / len(scores) if scores else 0.0
            total_weighted += avg_score * skill.weight
            total_weight += skill.weight

            skill_breakdown.append({
                "name": skill.name,
                "weight": skill.weight,
                "score": round(avg_score, 3),
                "concepts_mastered": mastered_count,
                "concepts_total": len(skill.concept_ids),
                "status": "complete" if mastered_count == len(skill.concept_ids)
                    else "in_progress" if mastered_count > 0
                    else "not_started",
            })

            missing = [
                cid for cid in skill.concept_ids
                if not concept_states.get(cid) or concept_states[cid].get("status") != "mastered"
            ]
            if missing:
                gaps.append(SkillGap(
                    skill_name=skill.name,
                    current_mastery=round(avg_score, 3),
                    required_mastery=skill.minimum_mastery,
                    missing_concepts=missing,
                    estimated_hours=round(len(missing) * 2.0, 1),
                ))

        overall = total_weighted / total_weight if total_weight > 0 else 0.0
        gaps.sort(key=lambda g: next(
            (s.weight for s in role.required_skills if s.name == g.skill_name), 0
        ), reverse=True)

        recommended = None
        if gaps:
            recommended = gaps[0].missing_concepts[0] if gaps[0].missing_concepts else None

        return CareerReadiness(
            role_id=role.id,
            role_title=role.title,
            overall_score=round(overall, 3),
            skill_breakdown=skill_breakdown,
            gaps=gaps,
            estimated_hours_to_ready=round(sum(g.estimated_hours for g in gaps), 1),
            recommended_next=recommended,
        )

    def add_role(self, role: CareerRole):
        self.roles[role.id] = role

    def get_required_concepts(self, role_id: str) -> set[str]:
        role = self.roles.get(role_id)
        if not role:
            return set()
        concepts = set()
        for skill in role.required_skills:
            concepts.update(skill.concept_ids)
        return concepts


career_service = CareerService()
