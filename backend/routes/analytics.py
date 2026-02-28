import logging
from fastapi import APIRouter, HTTPException, Depends
from backend.services.learner_store import learner_store
from backend.auth.dependencies import get_current_user, verify_ownership
from backend.agents.analytics import analytics_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/{learner_id}")
async def get_analytics(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    return analytics_agent.compute_full_analytics(learner)


@router.get("/{learner_id}/patterns")
async def get_patterns(learner_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    return {
        "learner_id": learner_id,
        "patterns": analytics_agent.identify_learning_patterns(learner),
    }
