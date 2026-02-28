import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.services.learner_store import learner_store
from backend.auth.dependencies import get_current_user, verify_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/learner", tags=["learner"])


class UpdateCareerTargetRequest(BaseModel):
    role_ids: list[str]


@router.get("/{learner_id}/state")
async def get_state(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    mastered = sum(1 for cs in learner.concept_states.values() if cs.status == "mastered")
    resolved = sum(len(cs.misconceptions_resolved) for cs in learner.concept_states.values())
    gaps = sum(abs(cs.calibration_gap) for cs in learner.concept_states.values() if cs.calibration_gap != 0)
    count = sum(1 for cs in learner.concept_states.values() if cs.calibration_gap != 0)

    return {
        "learner_id": learner.learner_id,
        "name": learner.name,
        "concept_states": {cid: cs.model_dump() for cid, cs in learner.concept_states.items()},
        "learning_profile": learner.learning_profile.model_dump(),
        "career_targets": learner.career_targets,
        "stats": {
            "total_concepts_mastered": mastered,
            "total_misconceptions_resolved": resolved,
            "avg_calibration_gap": round(gaps / count, 3) if count else 0.0,
            "total_hours": learner.learning_profile.total_hours,
        },
    }


@router.get("/{learner_id}/calibration")
async def get_calibration(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    per_concept = []
    total_gap = 0.0
    count = 0
    for cid, cs in learner.concept_states.items():
        if cs.self_reported_confidence > 0 or cs.mastery_score > 0:
            per_concept.append({
                "concept": cid,
                "confidence": cs.self_reported_confidence,
                "mastery": cs.mastery_score,
                "gap": cs.calibration_gap,
            })
            total_gap += abs(cs.calibration_gap)
            count += 1

    return {
        "overall_calibration": round(total_gap / count, 3) if count else 0.0,
        "trend": learner.learning_profile.calibration_trend,
        "per_concept": per_concept,
    }


@router.get("/{learner_id}/rl-policy")
async def get_rl_policy(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    from backend.agents.rl_engine import get_rl_engine
    engine = get_rl_engine(learner)
    return {
        "learner_id": learner.learner_id,
        "policy_stats": engine.get_policy_stats(),
        "has_learned": bool(learner.rl_policy),
    }


@router.get("/{learner_id}/reviews")
async def get_reviews(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    from backend.agents.review_scheduler import review_scheduler
    return review_scheduler.get_queue_summary(learner)


@router.get("/{learner_id}/retention/{concept_id}")
async def get_retention(learner_id: str, concept_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    from backend.agents.review_scheduler import review_scheduler
    return review_scheduler.get_retention_curve(learner, concept_id)


@router.put("/{learner_id}/career-target")
async def update_career_target(learner_id: str, req: UpdateCareerTargetRequest, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    logger.info(f"Updating career targets for {learner_id}: {req.role_ids}")
    learner.career_targets = req.role_ids
    await learner_store.update_learner(learner)

    from backend.agents.career_mapper import career_mapper_agent
    readiness = career_mapper_agent.calculate_all_readiness(learner)
    return {"career_targets": learner.career_targets, "readiness": [r.model_dump() for r in readiness]}


@router.get("/{learner_id}/sessions")
async def get_sessions(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    sessions = await learner_store.get_learner_sessions(learner_id)
    return [
        {
            "session_id": s.session_id,
            "started_at": s.started_at.isoformat(),
            "current_concept": s.current_concept,
            "concepts_covered": s.concepts_covered,
            "concepts_mastered": s.concepts_mastered,
            "current_state": s.current_state,
        }
        for s in sessions
    ]
