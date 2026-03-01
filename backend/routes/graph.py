import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from backend.services.knowledge_graph import knowledge_graph
from backend.services.learner_store import learner_store
from backend.auth.dependencies import get_current_user, verify_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("")
async def get_graph(domain: list[str] = Query(default=[]), learner_id: str | None = None):
    try:
        learner_states = None
        learner_concepts = None
        if learner_id:
            learner = await learner_store.get_learner(learner_id)
            if learner:
                learner_states = {
                    cid: {
                        "status": cs.status,
                        "mastery_score": cs.mastery_score,
                        "confidence": cs.confidence,
                        "prerequisites": cs.prerequisites,
                    }
                    for cid, cs in learner.concept_states.items()
                }
                # Show ALL concepts in learner's roadmap (not just taught ones)
                learner_concepts = set(learner.concept_states.keys())

        domains = domain if domain else None
        data = knowledge_graph.get_graph_data(domains=domains, learner_states=learner_states)

        # Filter to only learner-relevant concepts if a learner is specified
        if learner_concepts is not None:
            data["nodes"] = [n for n in data["nodes"] if n["id"] in learner_concepts]
            node_ids = {n["id"] for n in data["nodes"]}
            data["edges"] = [
                e for e in data["edges"]
                if e["source"] in node_ids and e["target"] in node_ids
            ]

        return data
    except Exception as e:
        logger.error(f"Failed to fetch graph: {e}")
        raise HTTPException(500, f"Failed to fetch graph: {str(e)}")


@router.get("/concept/{concept_id}")
async def get_concept(concept_id: str):
    try:
        concept = knowledge_graph.get_concept(concept_id)
        if not concept:
            raise HTTPException(404, "Concept not found")
        return concept.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch concept {concept_id}: {e}")
        raise HTTPException(500, f"Failed to fetch concept: {str(e)}")


@router.get("/path/{learner_id}/{role_id}")
async def get_path(learner_id: str, role_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    from backend.agents.curriculum import curriculum_agent
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    try:
        path = curriculum_agent.generate_learning_path(learner, role_id)
        logger.info(f"Generated path for learner={learner_id}, role={role_id}: {len(path)} concepts")
        return {
            "path": path,
            "total_concepts": len(path),
            "total_hours": round(sum(s["estimated_hours"] for s in path), 1),
        }
    except Exception as e:
        logger.error(f"Failed to generate path for {learner_id}/{role_id}: {e}")
        raise HTTPException(500, f"Failed to generate learning path: {str(e)}")
