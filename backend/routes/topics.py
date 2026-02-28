import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from backend.auth.dependencies import get_current_user
from backend.services.concept_generator import concept_generator
from backend.services.knowledge_graph import knowledge_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


class GenerateTopicRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    depth: int = Field(default=10, ge=4, le=15)


class ExpandConceptRequest(BaseModel):
    concept_id: str
    direction: str = Field(default="deeper", pattern="^(deeper|lateral)$")


@router.post("/generate")
async def generate_topic(req: GenerateTopicRequest, user: dict = Depends(get_current_user)):
    """Generate a full concept tree for any topic using the LLM."""
    try:
        experience = user.get("experience_level", "beginner")
        concepts = await concept_generator.generate_concept_tree(
            topic=req.topic, depth=req.depth, learner_experience=experience
        )

        if not concepts:
            raise HTTPException(400, "Could not generate concepts for this topic")

        added = knowledge_graph.add_concepts(concepts)

        return {
            "topic": req.topic,
            "concepts_generated": len(concepts),
            "concepts_added": added,
            "domain": concepts[0].domain if concepts else None,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "domain": c.domain,
                    "description": c.description,
                    "difficulty_tier": c.difficulty_tier,
                    "prerequisites": c.prerequisites,
                    "tags": c.tags,
                    "base_hours": c.base_hours,
                }
                for c in concepts
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"topic generation failed: {e}")
        raise HTTPException(500, f"Generation failed: {str(e)}")


@router.post("/expand")
async def expand_concept(req: ExpandConceptRequest, user: dict = Depends(get_current_user)):
    """Expand an existing concept into deeper or lateral sub-concepts."""
    concept = knowledge_graph.get_concept(req.concept_id)
    if not concept:
        raise HTTPException(404, f"Concept {req.concept_id} not found")

    try:
        new_concepts = await concept_generator.expand_concept(concept, direction=req.direction)
        added = knowledge_graph.add_concepts(new_concepts)

        return {
            "parent_concept": req.concept_id,
            "direction": req.direction,
            "concepts_generated": len(new_concepts),
            "concepts_added": added,
            "concepts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "difficulty_tier": c.difficulty_tier,
                    "prerequisites": c.prerequisites,
                }
                for c in new_concepts
            ],
        }
    except Exception as e:
        logger.error(f"concept expansion failed: {e}")
        raise HTTPException(500, f"Expansion failed: {str(e)}")


@router.get("/domains")
async def list_domains():
    """List all available domains (both static and generated)."""
    return {
        "domains": knowledge_graph.domains,
        "total_concepts": len(knowledge_graph.get_all_concepts()),
    }


@router.get("/suggestions")
async def get_suggestions():
    """Return topic suggestions for the welcome screen."""
    suggestions = []
    for domain_info in knowledge_graph.domains:
        domain_id = domain_info["id"]
        concepts = knowledge_graph.get_domain_concepts(domain_id)
        suggestions.append({
            "domain": domain_info.get("name", domain_id),
            "domain_id": domain_id,
            "concepts": [
                {"id": c.id, "name": c.name, "description": c.description}
                for c in concepts[:5]
            ],
        })
    return {
        "suggestions": suggestions,
        "total_concepts": len(knowledge_graph.get_all_concepts()),
    }
