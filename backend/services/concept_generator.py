import json
import logging
from backend.models.concept import Concept, Misconception, MasteryCriteria
from backend.services.llm_client import llm_client

logger = logging.getLogger(__name__)


class ConceptGenerator:

    async def generate_concept_tree(self, topic: str, depth: int = 10,
                                    learner_experience: str = "beginner") -> list[Concept]:
        system = """You are an expert curriculum designer. Generate a structured learning path as a tree of concepts.
Each concept must have prerequisites that reference other concepts in YOUR output (by their id).
Order concepts from foundational to advanced. Use consistent id format: domain.concept_name (lowercase, underscores)."""

        prompt = f"""Generate a learning tree for: {topic}

TARGET DEPTH: {depth} concepts (minimum 6, maximum 15)
LEARNER LEVEL: {learner_experience}

For EACH concept, provide:
- id: unique identifier like "python.list_comp" or "ml.linear_regression"
- name: human readable name
- domain: broad category (e.g. "python", "ml", "web", "math", "rust")
- description: 2-3 sentence explanation of what this concept covers
- difficulty_tier: 1 (beginner) to 5 (expert)
- prerequisites: list of concept ids FROM THIS LIST that must be learned first (empty for foundational ones)
- common_misconceptions: list of 1-2 misconceptions, each with:
  - id: short identifier
  - description: what the learner gets wrong
  - indicators: 2-3 signs the learner has this misconception
  - remediation_strategy: one of "socratic", "worked_examples", "analogy", "debugging_exercise", "explain_back"
  - example_trigger: a question that would expose this misconception
- teaching_contexts: 2-3 real-world contexts where this concept appears
- test_contexts: 2-3 DIFFERENT contexts for transfer testing (must differ from teaching_contexts)
- base_hours: estimated hours to learn (0.5 - 8.0)
- tags: 2-4 relevant tags

CRITICAL RULES:
- Prerequisites must ONLY reference ids you define in this same output
- At least 2 concepts must have NO prerequisites (entry points)
- The graph must be a valid DAG (no circular dependencies)
- Concepts should progress logically from foundational to advanced

Return JSON: {{"domain": "domain_name", "domain_description": "...", "concepts": [...]}}"""

        result = await llm_client.generate(prompt=prompt, system=system)

        concepts = []
        raw_concepts = result.get("concepts", [])
        domain = result.get("domain", topic.lower().replace(" ", "_"))

        # collect all generated ids for prerequisite validation
        valid_ids = {c.get("id", "") for c in raw_concepts}

        for raw in raw_concepts:
            try:
                # validate prerequisites reference only ids in this batch
                prereqs = [p for p in raw.get("prerequisites", []) if p in valid_ids]

                misconceptions = []
                for m in raw.get("common_misconceptions", []):
                    misconceptions.append(Misconception(
                        id=m.get("id", "unknown"),
                        description=m.get("description", ""),
                        indicators=m.get("indicators", [])[:3],
                        remediation_strategy=m.get("remediation_strategy", "socratic"),
                        example_trigger=m.get("example_trigger", ""),
                    ))

                concept = Concept(
                    id=raw.get("id", f"{domain}.unknown"),
                    name=raw.get("name", "Unknown"),
                    domain=domain,
                    description=raw.get("description", ""),
                    difficulty_tier=max(1, min(5, int(raw.get("difficulty_tier", 1)))),
                    prerequisites=prereqs,
                    common_misconceptions=misconceptions,
                    mastery_criteria=MasteryCriteria(),
                    teaching_contexts=raw.get("teaching_contexts", [])[:3],
                    test_contexts=raw.get("test_contexts", [])[:3],
                    tags=raw.get("tags", []),
                    base_hours=max(0.5, min(8.0, float(raw.get("base_hours", 2.0)))),
                )
                concepts.append(concept)
            except Exception as e:
                logger.warning(f"skipping malformed concept: {e}")
                continue

        logger.info(f"generated {len(concepts)} concepts for topic '{topic}'")
        return concepts

    async def expand_concept(self, parent_concept: Concept, direction: str = "deeper") -> list[Concept]:
        system ="You are an expert curriculum designer expanding an existing learning path."
        prompt = f"""The learner has mastered or is studying: {parent_concept.name}
Description: {parent_concept.description}
Domain: {parent_concept.domain}

Generate 3-5 {direction} concepts that build on this.
{"Go deeper into subtopics and advanced applications." if direction == "deeper" else "Explore related lateral topics the learner should know."}

Each concept must have {parent_concept.id} as a prerequisite.
Use the same domain: {parent_concept.domain}

Return JSON: {{"concepts": [same format as before with id, name, domain, description, difficulty_tier, prerequisites, common_misconceptions, teaching_contexts, test_contexts, base_hours, tags]}}"""

        result = await llm_client.generate(prompt=prompt, system=system)

        concepts = []
        for raw in result.get("concepts", []):
            try:
                prereqs = raw.get("prerequisites", [parent_concept.id])
                if parent_concept.id not in prereqs:
                    prereqs.insert(0, parent_concept.id)

                misconceptions = []
                for m in raw.get("common_misconceptions", []):
                    misconceptions.append(Misconception(
                        id=m.get("id", "unknown"),
                        description=m.get("description", ""),
                        indicators=m.get("indicators", [])[:3],
                        remediation_strategy=m.get("remediation_strategy", "socratic"),
                        example_trigger=m.get("example_trigger", ""),
                    ))

                concept = Concept(
                    id=raw.get("id", f"{parent_concept.domain}.expanded"),
                    name=raw.get("name", "Unknown"),
                    domain=parent_concept.domain,
                    description=raw.get("description", ""),
                    difficulty_tier=max(1, min(5, int(raw.get("difficulty_tier", parent_concept.difficulty_tier + 1)))),
                    prerequisites=prereqs,
                    common_misconceptions=misconceptions,
                    mastery_criteria=MasteryCriteria(),
                    teaching_contexts=raw.get("teaching_contexts", [])[:3],
                    test_contexts=raw.get("test_contexts", [])[:3],
                    tags=raw.get("tags", []),
                    base_hours=max(0.5, min(8.0, float(raw.get("base_hours", 2.0)))),
                )
                concepts.append(concept)
            except Exception as e:
                logger.warning(f"skipping malformed expanded concept: {e}")
                continue

        return concepts


concept_generator = ConceptGenerator()
