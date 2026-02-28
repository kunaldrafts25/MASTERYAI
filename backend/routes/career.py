import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.services.career_service import career_service
from backend.services.career_role_generator import career_role_generator
from backend.services.learner_store import learner_store
from backend.agents.career_mapper import career_mapper_agent
from backend.agents.curriculum import curriculum_agent
from backend.auth.dependencies import get_current_user, verify_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/career", tags=["career"])


class GenerateRoleRequest(BaseModel):
    role_description: str = Field(min_length=3, max_length=500)
    level: str = Field(default="mid", pattern="^(entry|mid|senior)$")


@router.post("/generate-role")
async def generate_role(req: GenerateRoleRequest, user: dict = Depends(get_current_user)):
    try:
        role, metadata = await career_role_generator.generate_role(
            role_description=req.role_description,
            level=req.level,
        )
        career_service.add_role(role)
        return {
            "role": role.model_dump(),
            "mapping": metadata,
            "message": f"Generated role '{role.title}' with {len(role.required_skills)} skill groups",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Career role generation failed: {e}")
        raise HTTPException(500, f"Role generation failed: {str(e)}")


@router.get("/roles")
async def get_roles():
    try:
        roles = career_service.get_all_roles()
        return [
            {
                "id": r.id,
                "title": r.title,
                "level": r.level,
                "market_demand": r.market_demand,
                "salary_range": r.salary_range,
                "growth_trend": r.growth_trend,
                "required_skills_count": len(r.required_skills),
                "total_concepts": sum(len(s.concept_ids) for s in r.required_skills),
            }
            for r in roles
        ]
    except Exception as e:
        logger.error(f"Failed to fetch roles: {e}")
        raise HTTPException(500, f"Failed to fetch roles: {str(e)}")


@router.get("/roles/{role_id}")
async def get_role(role_id: str):
    try:
        role = career_service.get_role(role_id)
        if not role:
            raise HTTPException(404, "Role not found")
        return role.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch role {role_id}: {e}")
        raise HTTPException(500, f"Failed to fetch role: {str(e)}")


@router.get("/readiness/{learner_id}/{role_id}")
async def get_readiness(learner_id: str, role_id: str, user: dict = Depends(get_current_user)):
    await verify_ownership(user, learner_id)
    learner = await learner_store.get_learner(learner_id)
    if not learner:
        raise HTTPException(404, "Learner not found")

    try:
        readiness = career_mapper_agent.calculate_readiness(learner, role_id)
        if not readiness:
            raise HTTPException(404, "Role not found")

        path = curriculum_agent.generate_learning_path(learner, role_id)
        logger.info(f"Readiness calculated for learner={learner_id}, role={role_id}")

        return {
            "readiness": readiness.model_dump(),
            "learning_path": path,
            "total_concepts": len(path),
            "total_hours": round(sum(s["estimated_hours"] for s in path), 1),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Readiness calculation failed for {learner_id}/{role_id}: {e}")
        raise HTTPException(500, f"Readiness calculation failed: {str(e)}")
